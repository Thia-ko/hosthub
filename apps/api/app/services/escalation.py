"""Deterministic (non-ML) rules for auto-escalating a WhatsApp conversation to a human.

Two triggers, both handled in `app.api.v1.routers.webhooks._maybe_auto_reply`:
1. The customer explicitly asks for a human (`customer_requests_handoff`), checked before any
   AI call - cheaper and works even when no AI provider is configured.
2. The AI itself signals it's unsure or the topic is sensitive, by prefixing its reply with
   `ESCALATION_TAG` as instructed in `ai_assist_provider.ESCALATION_SUFFIX` (`split_escalation_tag`).

Either trigger pauses the AI for that thread (`ConversationThread.ai_paused`) and marks it as
needing human attention (`ConversationThread.escalated`) rather than just "someone chose to
handle this personally" - the UI badges the two cases differently.
"""

ESCALATION_TAG = "[ESCALAR]"

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


def split_escalation_tag(reply: str) -> tuple[str, bool]:
    """If the AI prefixed its reply with `ESCALATION_TAG`, strips it and reports True so the
    caller pauses the thread. The remaining text is still sent to the customer as-is - the model
    is instructed to leave a short, polite handoff message after the tag."""
    stripped = reply.strip()
    if stripped.startswith(ESCALATION_TAG):
        return stripped[len(ESCALATION_TAG):].strip(), True
    return reply, False
