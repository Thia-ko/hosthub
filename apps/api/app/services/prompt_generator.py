import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models.attendant_pattern import AttendantPattern
from app.models.conversation_analysis import ConversationAnalysis
from app.models.extracted_data import ExtractedData
from app.models.faq_item import FaqItem
from app.models.instance import Instance
from app.models.prompt_version import PromptVersion, PromptVersionSource
from app.services.ai_assist_provider import OpenAiCompatibleProvider
from app.services.ai_settings import get_effective_ai_settings
from app.utils.json_utils import safe_parse_json_array

logger = logging.getLogger(__name__)

_AUTO_GEN_INTERVALS = {
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "1w": timedelta(weeks=1),
}


async def _collect_instance_data(db, instance_id) -> dict:
    async def _extracted(category: str) -> list[ExtractedData]:
        result = await db.execute(
            select(ExtractedData)
            .where(ExtractedData.instance_id == instance_id, ExtractedData.category == category)
            .order_by(ExtractedData.occurrences.desc())
        )
        return list(result.scalars().all())

    faqs_result = await db.execute(
        select(FaqItem).where(FaqItem.instance_id == instance_id).order_by(FaqItem.frequency.desc()).limit(30)
    )
    patterns_result = await db.execute(
        select(AttendantPattern)
        .where(AttendantPattern.instance_id == instance_id, AttendantPattern.pattern_type != "personality_trait")
        .order_by(AttendantPattern.frequency.desc())
    )
    traits_result = await db.execute(
        select(AttendantPattern)
        .where(AttendantPattern.instance_id == instance_id, AttendantPattern.pattern_type == "personality_trait")
        .order_by(AttendantPattern.frequency.desc())
    )

    return {
        "business_info": await _extracted("business_info"),
        "products": await _extracted("products_services"),
        "policies": await _extracted("policies"),
        "faqs": list(faqs_result.scalars().all()),
        "patterns": list(patterns_result.scalars().all()),
        "traits": list(traits_result.scalars().all()),
    }


def _format_collected_data(data: dict) -> str:
    def fmt(items: list[ExtractedData]) -> str:
        return "\n".join(f"- {item.key}: {item.value}" for item in items) or "(sem dados ainda)"

    fmt_faqs = (
        "\n\n".join(f"P: {faq.question}\nR: {faq.answer}" for faq in data["faqs"]) or "(sem FAQs ainda)"
    )

    def fmt_pattern(pattern: AttendantPattern) -> str:
        examples = safe_parse_json_array(pattern.examples)
        suffix = f"\n  Exemplos: {' | '.join(examples[:3])}" if examples else ""
        return f"- [{pattern.pattern_type}] {pattern.description}{suffix}"

    fmt_patterns = "\n".join(fmt_pattern(p) for p in data["patterns"]) or "(sem padroes ainda)"
    fmt_traits = "\n".join(f"- {trait.description}" for trait in data["traits"]) or "(sem tracos ainda)"

    return f"""## Informacoes do Negocio
{fmt(data["business_info"])}

## Produtos e Servicos
{fmt(data["products"])}

## Politicas
{fmt(data["policies"])}

## Perguntas Frequentes
{fmt_faqs}

## Padroes de Atendimento
{fmt_patterns}

## Tracos de Personalidade
{fmt_traits}"""


def _build_full_generation_prompt(data_block: str) -> str:
    return f"""Voce e um especialista em criar prompts para agentes de IA de atendimento WhatsApp.

Com base nos dados coletados de conversas reais deste negocio, gere um prompt completo e eficaz para um agente de IA.
O prompt deve capturar a identidade, tom e conhecimento do atendente humano original.

DADOS COLETADOS:

{data_block}

INSTRUCAO:
Gere o prompt seguindo EXATAMENTE esta estrutura de secoes (use os titulos exatos):

## Identidade
[Quem e o agente, nome do estabelecimento, missao]

## Tom e Personalidade
[Como o agente se comunica, nivel de formalidade, uso de emojis, etc.]

## Informacoes do Negocio
[Nome, endereco, horario de funcionamento, contato]

## Produtos e Servicos
[Lista completa com precos se disponivel]

## Politicas
[Pagamento, entrega, troca, cancelamento]

## Perguntas Frequentes
[Pares pergunta/resposta formatados]

## Regras de Atendimento
[Comportamentos obrigatorios e proibidos]

## Como Lidar com Situacoes Dificeis
[Reclamacoes, preco alto, indisponibilidade, escalada para humano]

Retorne SOMENTE JSON valido:
{{ "content": "o prompt completo aqui" }}"""


def _build_incremental_update_prompt(base_prompt: str, data_block: str) -> str:
    return f"""Voce e um especialista em otimizar prompts de IA para atendimento WhatsApp.

Voce recebeu o PROMPT ATUAL do agente e DADOS ATUALIZADOS coletados de conversas reais.

SUA TAREFA: Atualizar o prompt existente com as informacoes novas, fazendo o MINIMO de mudancas necessarias.

REGRAS OBRIGATORIAS:
1. PRESERVE a estrutura, formato, secoes, titulos e organizacao do prompt original
2. PRESERVE todas as regras de comportamento, tom e personalidade existentes
3. APENAS adicione ou atualize informacoes factuais (produtos, precos, FAQs, horarios, politicas)
4. NAO reescreva secoes inteiras - faca edicoes pontuais onde necessario
5. NAO mude o estilo de escrita, formatacao ou ordem das secoes
6. NAO remova informacoes existentes a menos que os dados mostrem que estao claramente incorretas
7. Se nao houver nada novo para adicionar, retorne o prompt original SEM ALTERACOES

PROMPT ATUAL DO AGENTE:
---
{base_prompt}
---

DADOS ATUALIZADOS COLETADOS:
---
{data_block}
---

Compare o prompt atual com os dados atualizados. Adicione apenas informacoes que estejam nos dados mas FALTAM no prompt, ou corrija informacoes que mudaram (ex: preco atualizado).

Retorne SOMENTE JSON valido:
{{ "content": "o prompt atualizado aqui" }}"""


async def _analyzed_thread_count(db, instance_id) -> int:
    return await db.scalar(
        select(func.count(func.distinct(ConversationAnalysis.sender_number))).where(
            ConversationAnalysis.instance_id == instance_id, ConversationAnalysis.raw_result.is_not(None)
        )
    )


async def has_enough_data(db, instance_id) -> bool:
    return (await _analyzed_thread_count(db, instance_id)) >= 1


async def get_data_readiness(db, instance_id) -> dict:
    analyzed = await _analyzed_thread_count(db, instance_id)
    total_faqs = await db.scalar(select(func.count()).select_from(FaqItem).where(FaqItem.instance_id == instance_id))
    total_extracted = await db.scalar(
        select(func.count()).select_from(ExtractedData).where(ExtractedData.instance_id == instance_id)
    )
    total_patterns = await db.scalar(
        select(func.count()).select_from(AttendantPattern).where(
            AttendantPattern.instance_id == instance_id, AttendantPattern.pattern_type != "personality_trait"
        )
    )
    return {
        "analyzed_conversations": analyzed or 0,
        "total_faqs": total_faqs or 0,
        "total_extracted": total_extracted or 0,
        "total_patterns": total_patterns or 0,
        "ready": (analyzed or 0) >= 1,
    }


async def generate_prompt_from_data(db, instance: Instance) -> PromptVersion | None:
    """Generates a prompt from all collected data and saves it as a PENDING version - it never
    touches `instance.current_prompt_version_id`, so it requires explicit human approval before
    it can go live. Returns None if there isn't enough analyzed data yet."""
    if not await has_enough_data(db, instance.id):
        logger.info("Not enough data for instance %s. Skipping prompt generation.", instance.id)
        return None

    effective = await get_effective_ai_settings(db)
    provider = OpenAiCompatibleProvider(effective.api_key, effective.base_url, effective.model, effective.transcribe_model)
    if not provider.is_configured:
        logger.info("AI provider not configured; skipping prompt generation for instance %s", instance.id)
        return None

    data = await _collect_instance_data(db, instance.id)
    data_block = _format_collected_data(data)

    base_version = (
        await db.get(PromptVersion, instance.current_prompt_version_id)
        if instance.current_prompt_version_id
        else None
    )
    is_incremental = base_version is not None
    user_prompt = (
        _build_incremental_update_prompt(base_version.content, data_block)
        if is_incremental
        else _build_full_generation_prompt(data_block)
    )
    system_message = (
        "Voce atualiza prompts existentes de IA para atendimento WhatsApp com mudancas minimas e pontuais. "
        "Retorne somente JSON valido."
        if is_incremental
        else "Voce gera prompts de IA para agentes de atendimento WhatsApp. Retorne somente JSON valido."
    )

    try:
        parsed, _prompt_tokens, _completion_tokens = await provider.extract_json(
            system_message, user_prompt, temperature=0.2 if is_incremental else 0.4
        )
    except Exception:
        logger.exception("Prompt generation call failed for instance %s", instance.id)
        raise

    content = parsed.get("content") if isinstance(parsed, dict) else None
    if not content:
        raise ValueError("Resposta do provedor de IA nao contem um prompt gerado valido")

    analyzed_count = await _analyzed_thread_count(db, instance.id)
    change_note = (
        f"Otimizacao automatica ({analyzed_count} conversas analisadas)"
        if is_incremental
        else f"Criacao automatica ({analyzed_count} conversas analisadas)"
    )

    next_number = (
        await db.scalar(select(func.coalesce(func.max(PromptVersion.version_number), 0)).where(
            PromptVersion.instance_id == instance.id
        ))
    ) + 1

    version = PromptVersion(
        instance_id=instance.id,
        version_number=next_number,
        content=content,
        source=PromptVersionSource.AUTO_GENERATED,
        change_note=change_note,
        created_by_user_id=instance.created_by_admin_id,
        is_pending=True,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    logger.info(
        "Saved PENDING prompt v%d for instance %s (%s)",
        version.version_number, instance.id, "incremental" if is_incremental else "full",
    )
    return version


async def maybe_auto_generate_prompt(db, instance: Instance) -> None:
    """Mirrors the analyzer's auto-trigger: conversation-count threshold (default) or a
    configurable time interval, whichever the instance is set to use."""
    if not instance.auto_generate_prompt:
        return

    time_mode = instance.auto_gen_interval and instance.auto_gen_interval != "off"
    if time_mode:
        min_delta = _AUTO_GEN_INTERVALS.get(instance.auto_gen_interval)
        if min_delta is None:
            return
        elapsed = (
            datetime.now(timezone.utc) - instance.last_auto_gen_at
            if instance.last_auto_gen_at
            else None
        )
        if elapsed is not None and elapsed < min_delta:
            return
    else:
        analyzed = await _analyzed_thread_count(db, instance.id)
        threshold = instance.auto_gen_conversation_threshold or 5
        if analyzed == 0 or analyzed % threshold != 0:
            return

    # Skip if there's already an un-reviewed pending prompt waiting for approval.
    existing_pending = await db.scalar(
        select(func.count()).select_from(PromptVersion).where(
            PromptVersion.instance_id == instance.id, PromptVersion.is_pending.is_(True)
        )
    )
    if existing_pending:
        return

    version = await generate_prompt_from_data(db, instance)
    if version is not None:
        instance.last_auto_gen_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info("Auto-generated pending prompt v%d for instance %s", version.version_number, instance.id)
