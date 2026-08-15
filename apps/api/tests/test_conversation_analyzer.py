"""Unit tests for the pure helpers in app.services.conversation_analyzer: FAQ dedup similarity
and transcript building. The DB-backed merge/analysis flow isn't covered here (no async DB
fixtures in this suite - see the other test files for the established pattern)."""

from types import SimpleNamespace

from app.models.conversation_message import MessageDirection
from app.services.conversation_analyzer import _build_transcript, _similarity


def _message(text: str, direction: MessageDirection) -> SimpleNamespace:
    return SimpleNamespace(text=text, direction=direction)


# --- _similarity (Jaccard over word sets, used to dedupe near-identical FAQs) -------------------


def test_similarity_identical_strings_is_one():
    assert _similarity("qual o horario de funcionamento", "qual o horario de funcionamento") == 1.0


def test_similarity_completely_different_strings_is_zero():
    assert _similarity("qual o horario", "aceita cartao de credito") == 0.0


def test_similarity_partial_word_overlap_is_between_zero_and_one():
    score = _similarity("qual o horario de funcionamento", "qual o horario de hoje")
    assert 0.0 < score < 1.0


def test_similarity_both_empty_strings_is_one():
    # Degenerate case: two blank FAQ questions are trivially "the same" - avoids a 0/0 divide.
    assert _similarity("", "") == 1.0


def test_similarity_is_symmetric():
    a, b = "voces entregam aos sabados", "entrega aos sabados voces fazem"
    assert _similarity(a, b) == _similarity(b, a)


# --- _build_transcript (renders a thread as "Cliente:"/"Atendente:" lines for the AI prompt) ----


def test_build_transcript_labels_inbound_as_cliente_and_outbound_as_atendente():
    messages = [
        _message("Oi, voces tem entrega?", MessageDirection.INBOUND),
        _message("Sim, entregamos em toda a cidade", MessageDirection.OUTBOUND),
    ]

    transcript = _build_transcript(messages)

    assert transcript == "Cliente: Oi, voces tem entrega?\nAtendente: Sim, entregamos em toda a cidade"


def test_build_transcript_empty_list_is_empty_string():
    assert _build_transcript([]) == ""


def test_build_transcript_preserves_message_order():
    messages = [
        _message("primeira", MessageDirection.INBOUND),
        _message("segunda", MessageDirection.OUTBOUND),
        _message("terceira", MessageDirection.INBOUND),
    ]

    lines = _build_transcript(messages).split("\n")

    assert lines == ["Cliente: primeira", "Atendente: segunda", "Cliente: terceira"]
