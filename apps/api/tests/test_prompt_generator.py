"""Unit tests for the pure helpers in app.services.prompt_generator: the collected-data
formatter used to build the AI prompt, and the auto-generation trigger decision (conversation
threshold vs. time interval). DB-backed generation itself isn't covered here (no async DB
fixtures in this suite - see the other test files for the established pattern)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.prompt_generator import _format_collected_data, _is_auto_gen_due

NOW = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)


def _instance(**overrides) -> SimpleNamespace:
    defaults = {
        "auto_gen_interval": "off",
        "auto_gen_conversation_threshold": 5,
        "last_auto_gen_at": None,
    }
    return SimpleNamespace(**{**defaults, **overrides})


def _empty_data() -> dict:
    return {"business_info": [], "products": [], "policies": [], "faqs": [], "patterns": [], "traits": []}


# --- _format_collected_data ---------------------------------------------------------------------


def test_format_collected_data_empty_uses_placeholders_for_every_section():
    block = _format_collected_data(_empty_data())

    assert "(sem dados ainda)" in block
    assert "(sem FAQs ainda)" in block
    assert "(sem padroes ainda)" in block
    assert "(sem tracos ainda)" in block


def test_format_collected_data_renders_extracted_facts_as_key_value_lines():
    data = _empty_data()
    data["business_info"] = [SimpleNamespace(key="nome", value="Padaria do Ze")]

    block = _format_collected_data(data)

    assert "- nome: Padaria do Ze" in block


def test_format_collected_data_renders_faqs_as_question_answer_pairs():
    data = _empty_data()
    data["faqs"] = [SimpleNamespace(question="Voces entregam?", answer="Sim, gratis acima de R$50")]

    block = _format_collected_data(data)

    assert "P: Voces entregam?" in block
    assert "R: Sim, gratis acima de R$50" in block


def test_format_collected_data_renders_pattern_examples_capped_at_three():
    data = _empty_data()
    data["patterns"] = [
        SimpleNamespace(
            pattern_type="greeting",
            description="Cumprimenta pelo nome",
            examples='["Oi Joao!", "Ola Maria!", "E ai Pedro!", "Fala Ana!"]',
        )
    ]

    block = _format_collected_data(data)

    assert "[greeting] Cumprimenta pelo nome" in block
    assert "Oi Joao! | Ola Maria! | E ai Pedro!" in block
    assert "Fala Ana!" not in block


# --- _is_auto_gen_due: time-based interval mode --------------------------------------------------


def test_time_mode_fires_on_first_run_with_no_prior_generation():
    instance = _instance(auto_gen_interval="1d", last_auto_gen_at=None)

    assert _is_auto_gen_due(instance, analyzed_count=0, now=NOW) is True


def test_time_mode_does_not_fire_before_the_interval_elapses():
    instance = _instance(auto_gen_interval="1d", last_auto_gen_at=NOW - timedelta(hours=2))

    assert _is_auto_gen_due(instance, analyzed_count=0, now=NOW) is False


def test_time_mode_fires_once_the_interval_has_elapsed():
    instance = _instance(auto_gen_interval="1d", last_auto_gen_at=NOW - timedelta(days=1, minutes=1))

    assert _is_auto_gen_due(instance, analyzed_count=0, now=NOW) is True


def test_time_mode_respects_longer_intervals():
    instance = _instance(auto_gen_interval="1w", last_auto_gen_at=NOW - timedelta(days=3))

    assert _is_auto_gen_due(instance, analyzed_count=0, now=NOW) is False


def test_time_mode_ignores_analyzed_count_entirely():
    instance = _instance(auto_gen_interval="1d", last_auto_gen_at=None)

    # analyzed_count=0 would never fire the count-based trigger, but time mode doesn't care.
    assert _is_auto_gen_due(instance, analyzed_count=0, now=NOW) is True


# --- _is_auto_gen_due: conversation-count threshold mode ("off" interval) -----------------------


def test_count_mode_does_not_fire_with_zero_analyzed_conversations():
    instance = _instance(auto_gen_interval="off", auto_gen_conversation_threshold=5)

    assert _is_auto_gen_due(instance, analyzed_count=0, now=NOW) is False


def test_count_mode_fires_exactly_at_the_threshold():
    instance = _instance(auto_gen_interval="off", auto_gen_conversation_threshold=5)

    assert _is_auto_gen_due(instance, analyzed_count=5, now=NOW) is True


def test_count_mode_does_not_fire_between_threshold_multiples():
    instance = _instance(auto_gen_interval="off", auto_gen_conversation_threshold=5)

    assert _is_auto_gen_due(instance, analyzed_count=6, now=NOW) is False


def test_count_mode_fires_again_at_the_next_multiple():
    instance = _instance(auto_gen_interval="off", auto_gen_conversation_threshold=5)

    assert _is_auto_gen_due(instance, analyzed_count=10, now=NOW) is True


def test_count_mode_falls_back_to_five_when_threshold_is_zero():
    instance = _instance(auto_gen_interval="off", auto_gen_conversation_threshold=0)

    assert _is_auto_gen_due(instance, analyzed_count=5, now=NOW) is True
    assert _is_auto_gen_due(instance, analyzed_count=3, now=NOW) is False
