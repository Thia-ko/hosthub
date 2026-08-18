"""
Unit tests for inbound WhatsApp payload parsing (app.services.whatsapp_channel).

These pin down the *confirmed* behavior for WhatsBotMais and Evolution API webhooks. The
audio/image mediaType values (`_AUDIO_MEDIA_TYPES` / `_IMAGE_MEDIA_TYPES`) were CONFIRMED
against real production traffic on 2026-08-18 - see docs/integrations/whatsbotmais.md. That
same traffic also caught a real bug: document/PDF attachments carry mediaType "application"
(not "document"), which fell through to plain-text handling with the filename as the message
body before the fix in `_UNSUPPORTED_MEDIA_TYPES`.
"""

from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.whatsapp_channel import (
    WhatsAppChannelError,
    parse_inbound_message,
    send_reply,
    send_text_message,
    send_whatsbotmais_reply,
)

# --- WhatsBotMais: text messages -------------------------------------------------------------


def test_whatsbotmais_text_message_parses():
    payload = {
        "mensagem": {
            "id": 8824203,
            "fromMe": False,
            "body": "Ola, preciso de ajuda",
            "mediaType": "conversation",
            "contact": {"number": "557991358293", "name": "Cliente"},
        },
        "sender": "557991358293",
        "fromMe": False,
        "token_origin": "AbCdEfGhIjKlMnOp",
        "ticket": {},
        "ticketData": {},
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.sender_number == "557991358293"
    assert parsed.text == "Ola, preciso de ajuda"
    assert parsed.whatsbotmais_token == "AbCdEfGhIjKlMnOp"
    assert parsed.media_kind is None


def test_whatsbotmais_blank_text_is_ignored():
    payload = {
        "mensagem": {"fromMe": False, "body": "   ", "mediaType": "conversation"},
        "sender": "557991358293",
        "token_origin": "tok",
    }

    assert parse_inbound_message(payload) is None


def test_whatsbotmais_unwraps_n8n_webhook_item_shape():
    payload = {
        "headers": {"content-type": "application/json"},
        "query": {},
        "body": {
            "mensagem": {"fromMe": False, "body": "Oi", "mediaType": "conversation"},
            "sender": "557991358293",
            "token_origin": "tok",
        },
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.text == "Oi"


# --- WhatsBotMais: echoes / missing data ------------------------------------------------------


def test_whatsbotmais_own_echo_at_root_is_ignored():
    payload = {
        "mensagem": {"fromMe": False, "body": "Oi", "mediaType": "conversation"},
        "sender": "557991358293",
        "fromMe": True,
        "token_origin": "tok",
    }

    assert parse_inbound_message(payload) is None


def test_whatsbotmais_own_echo_inside_mensagem_is_ignored():
    payload = {
        "mensagem": {"fromMe": True, "body": "Oi", "mediaType": "conversation"},
        "sender": "557991358293",
        "token_origin": "tok",
    }

    assert parse_inbound_message(payload) is None


def test_whatsbotmais_missing_token_is_ignored():
    payload = {
        "mensagem": {"fromMe": False, "body": "Oi", "mediaType": "conversation"},
        "sender": "557991358293",
    }

    assert parse_inbound_message(payload) is None


def test_whatsbotmais_missing_sender_falls_back_to_contact_number():
    payload = {
        "mensagem": {
            "fromMe": False,
            "body": "Oi",
            "mediaType": "conversation",
            "contact": {"number": "557991358293"},
        },
        "token_origin": "tok",
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.sender_number == "557991358293"


# --- WhatsBotMais: media --------------------------------------------------------------------


def test_whatsbotmais_audio_message_parses_as_media():
    payload = {
        "mensagem": {
            "fromMe": False,
            "body": "",
            "mediaType": "audio",
            "mediaUrl": "https://cdn.example.com/audio.ogg",
        },
        "sender": "557991358293",
        "token_origin": "tok",
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.media_kind == "audio"
    assert parsed.media_url == "https://cdn.example.com/audio.ogg"


def test_whatsbotmais_ptt_message_parses_as_audio():
    payload = {
        "mensagem": {"fromMe": False, "body": "", "mediaType": "ptt", "mediaUrl": "https://cdn.example.com/a.ogg"},
        "sender": "557991358293",
        "token_origin": "tok",
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.media_kind == "audio"


def test_whatsbotmais_image_message_parses_with_caption():
    payload = {
        "mensagem": {
            "fromMe": False,
            "body": "olha isso",
            "mediaType": "image",
            "mediaUrl": "https://cdn.example.com/foto.jpg",
        },
        "sender": "557991358293",
        "token_origin": "tok",
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.media_kind == "image"
    assert parsed.media_url == "https://cdn.example.com/foto.jpg"
    assert parsed.text == "olha isso"


def test_whatsbotmais_media_without_url_is_ignored():
    payload = {
        "mensagem": {"fromMe": False, "body": "", "mediaType": "image"},
        "sender": "557991358293",
        "token_origin": "tok",
    }

    assert parse_inbound_message(payload) is None


def test_whatsbotmais_unsupported_media_type_is_ignored():
    for media_type in ("video", "document", "application", "sticker", "location", "vcard", "contact", "contactsArray"):
        payload = {
            "mensagem": {"fromMe": False, "body": "", "mediaType": media_type, "mediaUrl": "x"},
            "sender": "557991358293",
            "token_origin": "tok",
        }
        assert parse_inbound_message(payload) is None, f"expected {media_type} to be ignored"


def test_whatsbotmais_document_attachment_does_not_leak_filename_as_text():
    """Regression test from a real payload captured 2026-08-18: a PDF sent to a live WhatsBotMais
    connection carries mediaType "application" and `mensagem.body` set to the *filename*, not
    customer text. Before `_UNSUPPORTED_MEDIA_TYPES` included "application", this fell through to
    the plain-text branch and the auto-reply pipeline would have replied to the filename string."""
    payload = {
        "mensagem": {
            "fromMe": False,
            "body": "11422dcf-8600-43c3-9332-445a4c055ccd_WhatsBot_Mais_Demonstracao.pdf",
            "mediaType": "application",
            "mediaUrl": "https://object.sp2.eveo.com.br/.../WhatsBot_Mais_Demonstracao.pdf",
        },
        "sender": "557991358293",
        "token_origin": "tok",
    }

    assert parse_inbound_message(payload) is None


def test_whatsbotmais_audio_classification_is_logged(caplog):
    payload = {
        "mensagem": {
            "fromMe": False,
            "body": "",
            "mediaType": "audio",
            "mediaUrl": "https://cdn.example.com/audio.ogg",
        },
        "sender": "557991358293",
        "token_origin": "tok",
    }

    with caplog.at_level("INFO", logger="app.services.whatsapp_channel"):
        parse_inbound_message(payload)

    assert any("classified as audio" in record.message for record in caplog.records)
    assert any("'audio'" in record.message for record in caplog.records)


def test_whatsbotmais_unrecognized_media_type_logs_a_warning(caplog):
    """A mediaType outside every known bucket (audio/image/unsupported) must not fail silently:
    it falls back to text-only handling and drops the actual media, so it has to be logged loudly
    enough to catch in production before it's mistaken for correct behavior."""
    payload = {
        "mensagem": {"fromMe": False, "body": "legenda", "mediaType": "some-new-type"},
        "sender": "557991358293",
        "token_origin": "tok",
    }

    with caplog.at_level("WARNING", logger="app.services.whatsapp_channel"):
        parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.text == "legenda"
    assert parsed.media_kind is None
    assert any("unrecognized mediaType" in record.message for record in caplog.records)


# --- Evolution API -----------------------------------------------------------------------------


def test_evolution_text_message_parses():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "557991358293@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "Oi, tudo bem?"},
        },
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.sender_number == "557991358293"
    assert parsed.text == "Oi, tudo bem?"
    assert parsed.whatsbotmais_token is None


def test_evolution_extended_text_message_parses():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "557991358293@s.whatsapp.net", "fromMe": False},
            "message": {"extendedTextMessage": {"text": "resposta citada"}},
        },
    }

    parsed = parse_inbound_message(payload)

    assert parsed is not None
    assert parsed.text == "resposta citada"


def test_evolution_ignores_non_upsert_events():
    payload = {"event": "connection.update", "data": {}}

    assert parse_inbound_message(payload) is None


def test_evolution_ignores_own_echo():
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "557991358293@s.whatsapp.net", "fromMe": True},
            "message": {"conversation": "Oi"},
        },
    }

    assert parse_inbound_message(payload) is None


def test_unrecognized_payload_shape_returns_none():
    assert parse_inbound_message({}) is None
    assert parse_inbound_message({"acao": "fila-data", "mediaFolder": "x"}) is None


# --- Sending: fail-fast when a channel isn't configured -----------------------------------------


async def test_send_whatsbotmais_reply_raises_when_base_url_missing(monkeypatch):
    monkeypatch.setattr(settings, "WHATSBOTMAIS_API_BASE_URL", "")

    with pytest.raises(WhatsAppChannelError, match="WhatsBotMais"):
        await send_whatsbotmais_reply("tok", "557991358293", "oi")


async def test_send_text_message_raises_when_evolution_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_API_BASE_URL", "")
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "")

    with pytest.raises(WhatsAppChannelError, match="Evolution API"):
        await send_text_message("minha-instancia", "557991358293", "oi")


async def test_send_text_message_raises_when_only_api_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "EVOLUTION_API_BASE_URL", "https://evolution.example.com")
    monkeypatch.setattr(settings, "EVOLUTION_API_KEY", "")

    with pytest.raises(WhatsAppChannelError, match="Evolution API"):
        await send_text_message("minha-instancia", "557991358293", "oi")


# --- send_reply: WhatsBotMais token vs. Evolution instance name, whichever the instance has ------


async def test_send_reply_prefers_whatsbotmais_token_when_present(monkeypatch):
    calls = {}

    async def fake_whatsbotmais(token, number, text):
        calls["whatsbotmais"] = (token, number, text)

    async def fake_evolution(name, number, text):
        calls["evolution"] = (name, number, text)

    monkeypatch.setattr("app.services.whatsapp_channel.send_whatsbotmais_reply", fake_whatsbotmais)
    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", fake_evolution)
    instance = SimpleNamespace(whatsapp_instance_name="minha-instancia")

    await send_reply(instance, "557991358293", "oi", "tok-abc")

    assert calls == {"whatsbotmais": ("tok-abc", "557991358293", "oi")}


async def test_send_reply_falls_back_to_evolution_when_no_token(monkeypatch):
    calls = {}

    async def fake_whatsbotmais(token, number, text):
        calls["whatsbotmais"] = (token, number, text)

    async def fake_evolution(name, number, text):
        calls["evolution"] = (name, number, text)

    monkeypatch.setattr("app.services.whatsapp_channel.send_whatsbotmais_reply", fake_whatsbotmais)
    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", fake_evolution)
    instance = SimpleNamespace(
        whatsapp_instance_name="minha-instancia", whatsapp_provider=None, meta_phone_number_id=None, meta_access_token=None
    )

    await send_reply(instance, "557991358293", "oi", None)

    assert calls == {"evolution": ("minha-instancia", "557991358293", "oi")}


async def test_send_reply_raises_when_neither_channel_is_available():
    instance = SimpleNamespace(
        whatsapp_instance_name=None, whatsapp_provider=None, meta_phone_number_id=None, meta_access_token=None
    )

    with pytest.raises(WhatsAppChannelError, match="Nenhum canal"):
        await send_reply(instance, "557991358293", "oi", None)
