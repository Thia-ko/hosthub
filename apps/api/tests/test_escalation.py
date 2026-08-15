"""Unit tests for the deterministic auto-escalation rules (app.services.escalation)."""

from app.services.escalation import customer_requests_handoff, split_escalation_tag


# --- customer_requests_handoff -------------------------------------------------------------------


def test_detects_explicit_request_for_attendant():
    assert customer_requests_handoff("quero falar com um atendente") is True


def test_detects_request_case_insensitively():
    assert customer_requests_handoff("QUERO FALAR COM UM ATENDENTE HUMANO") is True


def test_detects_keyword_embedded_in_a_longer_sentence():
    assert customer_requests_handoff("bom dia, gostaria de falar com atendente sobre meu pedido") is True


def test_ordinary_messages_do_not_trigger_handoff():
    assert customer_requests_handoff("qual o horario de funcionamento?") is False
    assert customer_requests_handoff("quero agendar um corte de cabelo") is False


def test_empty_text_does_not_trigger_handoff():
    assert customer_requests_handoff("") is False


# --- split_escalation_tag ----------------------------------------------------------------------


def test_strips_leading_escalation_tag_and_reports_true():
    text, escalate = split_escalation_tag("[ESCALAR] Vou te transferir para um atendente humano.")

    assert text == "Vou te transferir para um atendente humano."
    assert escalate is True


def test_reply_without_tag_is_returned_unchanged():
    text, escalate = split_escalation_tag("Sim, atendemos de segunda a sabado.")

    assert text == "Sim, atendemos de segunda a sabado."
    assert escalate is False


def test_tag_must_be_at_the_start_not_just_present_anywhere():
    text, escalate = split_escalation_tag("Nao sei, mas o time pode usar [ESCALAR] se precisar.")

    assert text == "Nao sei, mas o time pode usar [ESCALAR] se precisar."
    assert escalate is False


def test_tolerates_leading_whitespace_before_the_tag():
    text, escalate = split_escalation_tag("   [ESCALAR]   Um momento, vou chamar alguem.")

    assert text == "Um momento, vou chamar alguem."
    assert escalate is True
