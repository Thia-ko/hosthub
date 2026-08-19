"""Unit tests for the pure parts of app.services.chatbot: menu formatting and matching a
customer's message against a node's children (numeric position or keyword substring)."""

import json
from types import SimpleNamespace

from app.services.chatbot import format_menu, is_reset_keyword, match_child


def _node(label: str, keywords: list[str] | None = None):
    return SimpleNamespace(label=label, keywords=json.dumps(keywords or []))


# --- format_menu -----------------------------------------------------------------------------


def test_format_menu_numbers_options_starting_at_one():
    menu = format_menu([_node("Vendas"), _node("Suporte"), _node("Financeiro")])

    assert menu == "1. Vendas\n2. Suporte\n3. Financeiro"


def test_format_menu_empty_list_is_empty_string():
    assert format_menu([]) == ""


# --- match_child -------------------------------------------------------------------------------


def test_match_child_by_numeric_position():
    children = [_node("Vendas"), _node("Suporte")]

    assert match_child("2", children) is children[1]


def test_match_child_by_numeric_position_ignores_surrounding_whitespace():
    children = [_node("Vendas"), _node("Suporte")]

    assert match_child("  1  ", children) is children[0]


def test_match_child_numeric_position_out_of_range_falls_back_to_no_match():
    children = [_node("Vendas"), _node("Suporte")]

    assert match_child("9", children) is None


def test_match_child_by_keyword_substring_case_insensitive():
    children = [_node("Vendas", ["vendas", "comprar"]), _node("Suporte", ["suporte", "ajuda"])]

    assert match_child("preciso de AJUDA com meu pedido", children) is children[1]


def test_match_child_keyword_takes_the_first_match_in_order():
    children = [_node("A", ["oi"]), _node("B", ["oi"])]

    assert match_child("oi", children) is children[0]


def test_match_child_no_match_returns_none():
    children = [_node("Vendas", ["vendas"]), _node("Suporte", ["suporte"])]

    assert match_child("qual o horario de funcionamento?", children) is None


def test_match_child_prefers_numeric_position_over_keyword():
    # "1" is a valid position, so it must not fall through to keyword matching even if some
    # child happens to have "1" as a keyword for something else.
    children = [_node("Vendas"), _node("Suporte", ["1"])]

    assert match_child("1", children) is children[0]


# --- is_reset_keyword --------------------------------------------------------------------------


def test_is_reset_keyword_matches_known_reset_phrases():
    assert is_reset_keyword("menu") is True
    assert is_reset_keyword("Menu") is True
    assert is_reset_keyword("  voltar  ") is True
    assert is_reset_keyword("inicio") is True
    assert is_reset_keyword("início") is True


def test_is_reset_keyword_does_not_match_ordinary_text():
    assert is_reset_keyword("quero saber o horario") is False
    assert is_reset_keyword("menu de sobremesas") is False
