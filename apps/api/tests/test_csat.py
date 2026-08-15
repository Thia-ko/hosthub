"""Unit tests for the CSAT rating parser (app.services.csat.parse_rating)."""

from app.services.csat import parse_rating


def test_parses_bare_digit():
    assert parse_rating("5") == 5
    assert parse_rating("1") == 1


def test_parses_digit_embedded_in_a_sentence():
    assert parse_rating("nota 4") == 4
    assert parse_rating("5 estrelas, adorei!") == 5


def test_returns_first_matching_digit_when_multiple_present():
    assert parse_rating("entre 3 e 4 eu diria 3") == 3


def test_returns_none_for_text_without_a_valid_digit():
    assert parse_rating("muito bom") is None
    assert parse_rating("obrigado") is None


def test_returns_none_for_out_of_range_digits():
    assert parse_rating("0") is None
    assert parse_rating("9") is None


def test_returns_none_for_empty_text():
    assert parse_rating("") is None
