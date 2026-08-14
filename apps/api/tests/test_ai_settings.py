"""Unit tests for the AI assist settings merge logic (app.services.ai_settings).

DB-configured values (app.models.ai_settings.AiSettings, edited from the admin panel) win over
the AI_ASSIST_* env vars field by field; a blank/unset DB field falls back to its env var.
"""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.ai_settings import api_key_source, merge_effective_ai_settings


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """Pin env defaults so these tests don't depend on whatever is in .env."""
    monkeypatch.setattr(settings, "AI_ASSIST_API_KEY", "env-key")
    monkeypatch.setattr(settings, "AI_ASSIST_BASE_URL", "https://env.example.com/v1")
    monkeypatch.setattr(settings, "AI_ASSIST_MODEL", "env-model")
    monkeypatch.setattr(settings, "AI_ASSIST_TRANSCRIBE_MODEL", "env-transcribe-model")


def _row(**overrides):
    defaults = {"api_key": None, "base_url": None, "model": None, "transcribe_model": None}
    return SimpleNamespace(**{**defaults, **overrides})


def test_no_row_falls_back_to_env_entirely():
    effective = merge_effective_ai_settings(None)

    assert effective.api_key == "env-key"
    assert effective.base_url == "https://env.example.com/v1"
    assert effective.model == "env-model"
    assert effective.transcribe_model == "env-transcribe-model"


def test_blank_row_falls_back_to_env_entirely():
    effective = merge_effective_ai_settings(_row())

    assert effective.api_key == "env-key"
    assert effective.base_url == "https://env.example.com/v1"
    assert effective.model == "env-model"
    assert effective.transcribe_model == "env-transcribe-model"


def test_db_values_win_field_by_field():
    row = _row(api_key="db-key", model="db-model")

    effective = merge_effective_ai_settings(row)

    assert effective.api_key == "db-key"
    assert effective.model == "db-model"
    # base_url/transcribe_model left blank in the DB row - still fall back to env.
    assert effective.base_url == "https://env.example.com/v1"
    assert effective.transcribe_model == "env-transcribe-model"


def test_fully_configured_row_ignores_env_entirely():
    row = _row(api_key="db-key", base_url="https://db.example.com/v1", model="db-model", transcribe_model="db-t")

    effective = merge_effective_ai_settings(row)

    assert effective.api_key == "db-key"
    assert effective.base_url == "https://db.example.com/v1"
    assert effective.model == "db-model"
    assert effective.transcribe_model == "db-t"


def test_api_key_source_none_when_neither_db_nor_env_has_a_key(monkeypatch):
    monkeypatch.setattr(settings, "AI_ASSIST_API_KEY", "")

    assert api_key_source(None) == "none"
    assert api_key_source(_row()) == "none"


def test_api_key_source_env_when_only_env_has_a_key():
    assert api_key_source(None) == "env"
    assert api_key_source(_row()) == "env"


def test_api_key_source_database_when_db_row_has_a_key():
    assert api_key_source(_row(api_key="db-key")) == "database"
