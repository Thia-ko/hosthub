import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.db.session import async_session
from app.models.attendant_pattern import AttendantPattern
from app.models.conversation_analysis import ConversationAnalysis
from app.models.conversation_message import ConversationMessage, MessageDirection
from app.models.extracted_data import ExtractedData
from app.models.faq_item import FaqItem
from app.models.instance import Instance
from app.services.ai_assist_provider import OpenAiCompatibleProvider
from app.services.ai_settings import get_effective_ai_settings
from app.utils.json_utils import safe_parse_json_array

logger = logging.getLogger(__name__)

# Re-analyze a customer thread every N new messages (both directions) since its last analysis.
# Deliberately a constant rather than a per-instance setting to keep the analysis trigger simple;
# `Instance.auto_gen_conversation_threshold` controls the separate, coarser prompt-generation trigger.
ANALYSIS_BATCH_SIZE = 6

SYSTEM_PROMPT = """Voce e um especialista em analise de conversas de atendimento WhatsApp.
Analise a conversa e extraia informacoes estruturadas sobre o negocio, padroes do atendente e duvidas frequentes.

Retorne SOMENTE um JSON valido com esta estrutura exata:

{
  "business_info": [
    { "key": "nome_estabelecimento", "value": "string", "confidence": 0.0 }
  ],
  "products_services": [
    { "key": "string", "value": "string", "confidence": 0.0 }
  ],
  "faqs": [
    {
      "question": "string",
      "answer": "string",
      "category": "string",
      "asked_by": "cliente|atendente"
    }
  ],
  "attendant_patterns": [
    {
      "type": "greeting|tone|closing|objection_handling|escalation|upsell",
      "description": "string",
      "examples": ["string"]
    }
  ],
  "policies": [
    { "key": "string", "value": "string", "confidence": 0.0 }
  ],
  "personality_traits": ["string"]
}

Diretrizes:
- Responda SEMPRE em portugues brasileiro. Todos os textos (description, examples, personality_traits, category, key, value) devem estar em portugues.
- business_info: nome, endereco, horario de funcionamento, telefone, cidade
- products_services: cada produto/servico com preco se disponivel
- faqs: capture perguntas de AMBOS os lados. Use asked_by "cliente" para duvidas feitas pelo cliente, e asked_by "atendente" para perguntas de qualificacao/abordagem usadas pelo atendente/IA. A "answer" e sempre a resposta recebida. Se nao houver perguntas, retorne []
- attendant_patterns: padroes de comportamento do atendente (saudacao, tom, fechamento, tratamento de objecoes). O campo "type" deve ser um dos valores fixos em ingles: greeting|tone|closing|objection_handling|escalation|upsell. Os campos "description" e "examples" devem estar em portugues.
- policies: pagamento, entrega, troca, cancelamento, garantia
- personality_traits: adjetivos/caracteristicas do estilo do atendente em portugues
- confidence: 0.0 a 1.0 indicando certeza baseada no que foi dito explicitamente
- Se nao houver dados para um campo, retorne array vazio []"""


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity on word sets - fast enough for short FAQ strings. Returns 0.0-1.0."""
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _build_transcript(messages: list[ConversationMessage]) -> str:
    lines = []
    for message in messages:
        speaker = "Cliente" if message.direction == MessageDirection.INBOUND else "Atendente"
        lines.append(f"{speaker}: {message.text}")
    return "\n".join(lines)


async def maybe_trigger_analysis(instance_id, sender_number: str) -> None:
    """Fire-and-forget entrypoint: schedule via `BackgroundTasks` after a webhook message is
    saved. Opens its own DB session/connection so it's safe to run after the request that
    triggered it has already returned its response. Never raises - failures are logged."""
    try:
        async with async_session() as db:
            instance = await db.get(Instance, instance_id)
            if instance is None:
                return

            total = await db.scalar(
                select(func.count()).select_from(ConversationMessage).where(
                    ConversationMessage.instance_id == instance_id,
                    ConversationMessage.sender_number == sender_number,
                )
            )
            last_analyzed_count = await db.scalar(
                select(func.max(ConversationAnalysis.message_count)).where(
                    ConversationAnalysis.instance_id == instance_id,
                    ConversationAnalysis.sender_number == sender_number,
                )
            )
            if (total or 0) - (last_analyzed_count or 0) < ANALYSIS_BATCH_SIZE:
                return

            await _analyze_thread(db, instance, sender_number, total or 0)
    except Exception:  # noqa: BLE001 - best-effort background pipeline, must never crash the caller
        logger.exception("Conversation analysis failed for instance %s / %s", instance_id, sender_number)


async def _analyze_thread(db, instance: Instance, sender_number: str, message_count: int) -> None:
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.instance_id == instance.id, ConversationMessage.sender_number == sender_number)
        .order_by(ConversationMessage.created_at)
    )
    messages = list(result.scalars().all())
    if not messages:
        return
    transcript = _build_transcript(messages)

    effective = await get_effective_ai_settings(db)
    provider = OpenAiCompatibleProvider(effective.api_key, effective.base_url, effective.model, effective.transcribe_model)
    if not provider.is_configured:
        logger.info("AI provider not configured; skipping conversation analysis for instance %s", instance.id)
        return

    logger.info("Analyzing thread %s for instance %s (%d messages)", sender_number, instance.id, len(messages))
    try:
        parsed, _prompt_tokens, _completion_tokens = await provider.extract_json(
            SYSTEM_PROMPT, f"Conversa para analise:\n\n{transcript}", temperature=0.2
        )
    except Exception as exc:  # noqa: BLE001 - record the failure, don't lose the trigger
        logger.exception("Analysis call failed for instance %s / %s", instance.id, sender_number)
        db.add(
            ConversationAnalysis(
                instance_id=instance.id,
                sender_number=sender_number,
                message_count=message_count,
                error=str(exc)[:500],
            )
        )
        await db.commit()
        return

    await _merge_analysis(db, instance.id, sender_number, parsed)
    db.add(
        ConversationAnalysis(
            instance_id=instance.id,
            sender_number=sender_number,
            message_count=message_count,
            raw_result=json.dumps(parsed, ensure_ascii=False),
        )
    )
    await db.commit()

    from app.services.prompt_generator import maybe_auto_generate_prompt

    try:
        await maybe_auto_generate_prompt(db, instance)
    except Exception:  # noqa: BLE001 - auto-generation is a bonus, analysis data is already saved
        logger.exception("Auto prompt generation failed for instance %s", instance.id)


async def _merge_analysis(db, instance_id, sender_number: str, result: dict) -> None:
    for category in ("business_info", "products_services", "policies"):
        await _merge_extracted_data(db, instance_id, category, result.get(category) or [], sender_number)
    await _merge_faqs(db, instance_id, result.get("faqs") or [])
    await _merge_patterns(db, instance_id, result.get("attendant_patterns") or [])
    await _merge_traits(db, instance_id, result.get("personality_traits") or [])


async def _merge_extracted_data(db, instance_id, category: str, items: list, source: str) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        key, value = item.get("key"), item.get("value")
        if not key or not value:
            continue
        confidence = float(item.get("confidence") or 0.5)

        existing_result = await db.execute(
            select(ExtractedData).where(
                ExtractedData.instance_id == instance_id,
                ExtractedData.category == category,
                ExtractedData.key == key,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            if confidence > existing.confidence:
                existing.value = value
                existing.confidence = confidence
            existing.occurrences += 1
        else:
            db.add(
                ExtractedData(
                    instance_id=instance_id, category=category, key=key, value=value,
                    confidence=confidence, source=source,
                )
            )


async def _merge_faqs(db, instance_id, faqs: list) -> None:
    existing_result = await db.execute(select(FaqItem).where(FaqItem.instance_id == instance_id))
    existing_faqs = list(existing_result.scalars().all())

    for faq in faqs:
        if not isinstance(faq, dict):
            continue
        question, answer = faq.get("question"), faq.get("answer")
        if not question or not answer:
            continue

        question_key = question.lower().strip()[:60]
        similar = next(
            (f for f in existing_faqs if _similarity(question_key, f.question.lower().strip()[:60]) >= 0.6), None
        )
        if similar:
            if len(answer) > len(similar.answer):
                similar.answer = answer
            similar.frequency += 1
            similar.last_seen_at = datetime.now(timezone.utc)
        else:
            new_faq = FaqItem(
                instance_id=instance_id,
                question=question,
                answer=answer,
                category=faq.get("category") or "geral",
                asked_by=faq.get("asked_by") or "cliente",
            )
            db.add(new_faq)
            existing_faqs.append(new_faq)  # avoid creating dupes within the same batch


async def _merge_patterns(db, instance_id, patterns: list) -> None:
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue
        pattern_type, description = pattern.get("type"), pattern.get("description")
        if not pattern_type or not description:
            continue
        examples = pattern.get("examples") or []
        if not isinstance(examples, list):
            examples = []

        existing_result = await db.execute(
            select(AttendantPattern).where(
                AttendantPattern.instance_id == instance_id, AttendantPattern.pattern_type == pattern_type
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            if len(description) > len(existing.description):
                existing.description = description
            merged = list(dict.fromkeys([*safe_parse_json_array(existing.examples), *examples]))[:10]
            existing.examples = json.dumps(merged, ensure_ascii=False)
            existing.frequency += 1
        else:
            db.add(
                AttendantPattern(
                    instance_id=instance_id, pattern_type=pattern_type, description=description,
                    examples=json.dumps(examples[:10], ensure_ascii=False),
                )
            )


async def _merge_traits(db, instance_id, traits: list) -> None:
    for trait in traits:
        if not trait:
            continue
        existing_result = await db.execute(
            select(AttendantPattern).where(
                AttendantPattern.instance_id == instance_id,
                AttendantPattern.pattern_type == "personality_trait",
                AttendantPattern.description == trait,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            existing.frequency += 1
        else:
            db.add(
                AttendantPattern(
                    instance_id=instance_id, pattern_type="personality_trait", description=trait, examples="[]"
                )
            )
