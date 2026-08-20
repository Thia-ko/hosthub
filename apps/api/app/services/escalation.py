"""Deterministic (non-ML) rules for auto-escalating a WhatsApp conversation to a human.

Two triggers, both handled in `app.api.v1.routers.webhooks._maybe_auto_reply`:
1. The customer explicitly asks for a human (`customer_requests_handoff`), checked before any
   AI call - cheaper and works even when no AI provider is configured. Which queue it lands in
   is resolved separately via a deterministic keyword match against each
   `AttendanceQueue.keywords` (see `app.services.queue.match_queue_by_keywords`), since no AI
   call happens on this path to ask the model directly.
2. The AI itself signals it's unsure or the topic is sensitive, by prefixing its reply with
   `ESCALATION_TAG` followed by `:<0-100>` (its own confidence that the reply so far resolves
   the issue) and, when the instance has more than one active queue, `:<queue-slug>` (which
   queue it thinks fits best, per `AttendanceQueue.routing_hint` listed in the instruction built
   by `build_escalation_suffix`) - parsed by `split_escalation_tag`.

Either trigger pauses the AI for that thread (`ConversationThread.ai_paused`) and marks it as
needing human attention (`ConversationThread.escalated`) rather than just "someone chose to
handle this personally" - the UI badges the two cases differently.
"""

import re
from dataclasses import dataclass
from typing import Sequence

ESCALATION_TAG = "[ESCALAR]"

_ESCALATION_PATTERN = re.compile(rf"^{re.escape(ESCALATION_TAG)}(?::(\d{{1,3}}))?(?::([a-z0-9-]+))?")

_HUMAN_HANDOFF_KEYWORDS = (
    "falar com atendente",
    "falar com um atendente",
    "falar com humano",
    "falar com um humano",
    "quero um atendente",
    "quero falar com alguem",
    "quero falar com alguém",
    "atendimento humano",
    "pessoa de verdade",
    "falar com uma pessoa",
)


def customer_requests_handoff(text: str) -> bool:
    """True if the customer's message explicitly asks to talk to a human, via substring match
    against a fixed keyword list. Deliberately simple: false negatives just fall through to the
    normal AI reply, false positives are a minor inconvenience (a human sees it sooner)."""
    normalized = text.lower()
    return any(keyword in normalized for keyword in _HUMAN_HANDOFF_KEYWORDS)


@dataclass(frozen=True)
class EscalationQueueOption:
    """One configured `AttendanceQueue` as offered to the AI for the `[ESCALAR:conf:slug]` tag -
    a plain dataclass (not the SQLAlchemy model) so `app.services.ai_assist_provider` doesn't
    need to import the ORM layer just to build a prompt."""

    slug: str
    name: str
    routing_hint: str | None


def build_escalation_suffix(queues: Sequence[EscalationQueueOption] = ()) -> str:
    """System-prompt suffix instructing the model when/how to escalate. With more than one
    queue configured, also asks it to pick the best-fitting one by slug so the conversation
    routes straight to the right team instead of a single catch-all queue - see the module
    docstring and `AttendanceQueue` for the full routing story."""
    suffix = (
        "\n\n---\n"
        "Se voce nao tiver certeza de como responder, ou o assunto for sensivel (reembolso, reclamacao "
        "grave, algo que foge do que voce sabe responder com as informacoes acima), comece sua resposta "
        f"com a tag {ESCALATION_TAG} seguida de dois-pontos e um numero de 0 a 100 indicando sua propria "
        "confianca de que a conversa ate agora resolve o problema do cliente"
    )
    if len(queues) > 1:
        options = "; ".join(
            f"'{queue.slug}' ({queue.name}" + (f": {queue.routing_hint}" if queue.routing_hint else "") + ")"
            for queue in queues
        )
        suffix += (
            f", mais dois-pontos e o identificador (slug) da fila mais adequada dentre estas: {options}. "
            f"Se nenhuma se encaixar claramente, use '{queues[0].slug}'. Exemplo: {ESCALATION_TAG}:40:{queues[0].slug}"
        )
    else:
        suffix += f" (ex: {ESCALATION_TAG}:40)"
    suffix += (
        ", depois uma mensagem curta e educada avisando que um atendente humano vai continuar o "
        "atendimento. So use essa tag quando realmente necessario."
    )
    return suffix


def split_escalation_tag(reply: str) -> tuple[str, bool, int | None, str | None]:
    """If the AI prefixed its reply with `ESCALATION_TAG`, strips it (and its optional
    `:<confidence>:<queue-slug>` suffix) and reports (escalate=True, confidence, queue_slug) so
    the caller pauses the thread, records how confident the AI was, and routes it into the
    chosen queue. The remaining text is still sent to the customer as-is - the model is
    instructed to leave a short, polite handoff message after the tag. `confidence`/`queue_slug`
    are None when absent or the model didn't follow the format; the caller falls back to the
    instance's default queue in that case (see `app.services.queue.resolve_default_queue`)."""
    stripped = reply.strip()
    match = _ESCALATION_PATTERN.match(stripped)
    if not match:
        return reply, False, None, None
    confidence_raw = match.group(1)
    confidence = min(int(confidence_raw), 100) if confidence_raw is not None else None
    queue_slug = match.group(2)
    return stripped[match.end():].strip(), True, confidence, queue_slug
