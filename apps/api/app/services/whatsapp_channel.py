import logging
from dataclasses import dataclass
from typing import Literal

import httpx

from app.core.config import settings
from app.models.instance import Instance, WhatsAppProvider

logger = logging.getLogger(__name__)

MediaKind = Literal["audio", "image"]


class WhatsAppChannelError(Exception):
    """Raised when a WhatsApp channel is not configured or the send call fails."""


@dataclass
class ParsedInboundMessage:
    sender_number: str
    text: str
    # WhatsBotMais: the Bearer token to use when replying (carried on every inbound event, no
    # per-instance configuration needed). None when the payload came from another provider
    # (e.g. Evolution API), which relies on `Instance.whatsapp_instance_name` instead.
    whatsbotmais_token: str | None = None
    # Set when this message is audio or an image we can still reply to (transcribe / vision).
    # `text` holds the caption when present (may be empty) - the actual content lives at media_url.
    media_kind: MediaKind | None = None
    media_url: str | None = None


async def send_whatsbotmais_reply(token: str, number: str, text: str) -> None:
    if not settings.WHATSBOTMAIS_API_BASE_URL:
        raise WhatsAppChannelError("WhatsBotMais nao configurado (WHATSBOTMAIS_API_BASE_URL)")

    async with httpx.AsyncClient(base_url=settings.WHATSBOTMAIS_API_BASE_URL, timeout=30) as client:
        try:
            response = await client.post(
                "/api/messages/sendOfficialData",
                headers={"Authorization": f"Bearer {token}"},
                json={"number": number, "text": text},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao enviar mensagem via WhatsBotMais: {exc}") from exc


async def send_text_message(whatsapp_instance_name: str, number: str, text: str) -> None:
    """Evolution API sender: used when Instance.whatsapp_instance_name identifies an Evolution
    connection rather than being just an on/off marker for WhatsBotMais."""
    if not settings.EVOLUTION_API_BASE_URL or not settings.EVOLUTION_API_KEY:
        raise WhatsAppChannelError("Evolution API nao configurada (EVOLUTION_API_BASE_URL/EVOLUTION_API_KEY)")

    async with httpx.AsyncClient(base_url=settings.EVOLUTION_API_BASE_URL, timeout=30) as client:
        try:
            response = await client.post(
                f"/message/sendText/{whatsapp_instance_name}",
                headers={"apikey": settings.EVOLUTION_API_KEY},
                json={"number": number, "text": text},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao enviar mensagem via Evolution API: {exc}") from exc


async def send_meta_cloud_reply(phone_number_id: str, access_token: str, number: str, text: str) -> None:
    url = f"https://graph.facebook.com/{settings.META_CLOUD_API_VERSION}/{phone_number_id}/messages"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": number,
                    "type": "text",
                    "text": {"body": text},
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao enviar mensagem via API Oficial (Meta): {exc}") from exc


async def validate_meta_credentials(phone_number_id: str, access_token: str) -> dict:
    """Real credential check against the Graph API before persisting a Meta Cloud connection -
    confirms the phone_number_id/access_token pair is valid and returns the phone's display
    metadata used to show the client what they just connected."""
    url = f"https://graph.facebook.com/{settings.META_CLOUD_API_VERSION}/{phone_number_id}"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "display_phone_number,verified_name"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao validar credenciais da API Oficial (Meta): {exc}") from exc
        return response.json()


def _require_evolution_config() -> None:
    if not settings.EVOLUTION_API_BASE_URL or not settings.EVOLUTION_API_KEY:
        raise WhatsAppChannelError("Evolution API nao configurada (EVOLUTION_API_BASE_URL/EVOLUTION_API_KEY)")


async def create_evolution_instance(instance_name: str) -> dict:
    _require_evolution_config()
    async with httpx.AsyncClient(base_url=settings.EVOLUTION_API_BASE_URL, timeout=30) as client:
        try:
            response = await client.post(
                "/instance/create",
                headers={"apikey": settings.EVOLUTION_API_KEY},
                json={"instanceName": instance_name, "qrcode": True},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao criar instancia na Evolution API: {exc}") from exc
        return response.json()


def _extract_evolution_qr(data: dict) -> dict:
    """Defensively pulls base64/code/pairingCode out of an Evolution API response, which may
    nest them under a `qrcode` key or place them at the top level depending on version."""
    qrcode_section = data.get("qrcode") if isinstance(data.get("qrcode"), dict) else data
    return {
        "base64": qrcode_section.get("base64") or data.get("base64"),
        "code": qrcode_section.get("code") or data.get("code"),
        "pairing_code": qrcode_section.get("pairingCode") or data.get("pairingCode"),
    }


async def get_evolution_qr(instance_name: str) -> dict:
    _require_evolution_config()
    async with httpx.AsyncClient(base_url=settings.EVOLUTION_API_BASE_URL, timeout=30) as client:
        try:
            response = await client.get(
                f"/instance/connect/{instance_name}",
                headers={"apikey": settings.EVOLUTION_API_KEY},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao obter QR code na Evolution API: {exc}") from exc
        return _extract_evolution_qr(response.json())


async def get_evolution_status(instance_name: str) -> str:
    _require_evolution_config()
    async with httpx.AsyncClient(base_url=settings.EVOLUTION_API_BASE_URL, timeout=30) as client:
        try:
            response = await client.get(
                f"/instance/connectionState/{instance_name}",
                headers={"apikey": settings.EVOLUTION_API_KEY},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao consultar status na Evolution API: {exc}") from exc
        data = response.json()
        instance_data = data.get("instance") if isinstance(data.get("instance"), dict) else data
        return str(instance_data.get("state", "close"))


async def delete_evolution_instance(instance_name: str) -> None:
    _require_evolution_config()
    async with httpx.AsyncClient(base_url=settings.EVOLUTION_API_BASE_URL, timeout=30) as client:
        try:
            # Best-effort: logout may 400 if the session is already closed - ignore and proceed
            # to delete regardless, since the goal is removing the instance either way.
            await client.delete(f"/instance/logout/{instance_name}", headers={"apikey": settings.EVOLUTION_API_KEY})
        except httpx.HTTPError:
            pass
        try:
            response = await client.delete(
                f"/instance/delete/{instance_name}",
                headers={"apikey": settings.EVOLUTION_API_KEY},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise WhatsAppChannelError(f"Falha ao excluir instancia na Evolution API: {exc}") from exc


async def send_reply(instance: Instance, sender_number: str, text: str, whatsbotmais_token: str | None) -> None:
    """Single decision point for outbound sends, shared by the reactive auto-reply (webhook)
    and the manual-reply endpoint: WhatsBotMais issues no per-instance credential, so a token
    captured from an inbound message is the only way to address that conversation; Meta Cloud
    and Evolution send by their own persisted per-instance credentials instead."""
    if whatsbotmais_token:
        await send_whatsbotmais_reply(whatsbotmais_token, sender_number, text)
    elif instance.whatsapp_provider == WhatsAppProvider.META_CLOUD and instance.meta_phone_number_id and instance.meta_access_token:
        await send_meta_cloud_reply(instance.meta_phone_number_id, instance.meta_access_token, sender_number, text)
    elif instance.whatsapp_instance_name:
        await send_text_message(instance.whatsapp_instance_name, sender_number, text)
    else:
        raise WhatsAppChannelError("Nenhum canal de WhatsApp configurado para esta instancia.")


# mediaType values below are now CONFIRMED against real production traffic captured 2026-08-18
# (raw `WebhookEvent.payload_json` rows for text/image/audio/document/video messages sent to a
# live WhatsBotMais connection): plain text carries mediaType "conversation"; audio and image
# carry exactly "audio"/"image" as originally inferred - no change needed there. Document/PDF
# attachments carry mediaType "application" (NOT "document" as originally guessed) - confirmed
# bug: without "application" in _UNSUPPORTED_MEDIA_TYPES, a PDF fell through to the plain-text
# branch with the *filename* as `text`, so the auto-reply pipeline would have replied to a
# filename string. "document" is kept alongside "application" defensively (e.g. a differently
# configured connection or provider version may still emit it), but "application" is the
# confirmed real value for a WhatsBotMais/Baileys connection. Video was already confirmed
# correctly ignored (no ConversationMessage created for it).
_AUDIO_MEDIA_TYPES = {"audio", "ptt"}
_IMAGE_MEDIA_TYPES = {"image"}
# Media we still can't act on (no reply channel for video/documents/etc via a text+vision agent).
_UNSUPPORTED_MEDIA_TYPES = {"video", "document", "application", "sticker", "location", "vcard", "contact", "contactsArray"}


def _parse_whatsbotmais_payload(payload: dict) -> ParsedInboundMessage | None:
    """
    Best-effort parse of a WhatsBotMais ticket-webhook payload (their own ticketing/queue format,
    confirmed from real production samples - not a raw WhatsApp provider webhook).
    """
    # WhatsBotMais posts the ticket payload directly; if it arrives wrapped in n8n's webhook-item
    # shape ({headers, body, query, ...}) instead, unwrap it first.
    if "body" in payload and "headers" in payload and isinstance(payload.get("body"), dict):
        payload = payload["body"]

    if payload.get("fromMe"):
        return None

    mensagem = payload.get("mensagem")
    if not isinstance(mensagem, dict) or mensagem.get("fromMe"):
        return None

    sender_number = payload.get("sender")
    if not sender_number:
        contact = mensagem.get("contact")
        sender_number = contact.get("number") if isinstance(contact, dict) else None
    if not isinstance(sender_number, str) or not sender_number:
        return None

    token = payload.get("token_origin")
    if not isinstance(token, str) or not token:
        return None

    text = mensagem.get("body") if isinstance(mensagem.get("body"), str) else ""
    media_type = mensagem.get("mediaType")

    if isinstance(media_type, str) and (media_type in _AUDIO_MEDIA_TYPES or media_type in _IMAGE_MEDIA_TYPES):
        media_url = mensagem.get("mediaUrl")
        if not isinstance(media_url, str) or not media_url:
            return None  # media message but nothing to fetch - nothing we can do
        media_kind: MediaKind = "audio" if media_type in _AUDIO_MEDIA_TYPES else "image"
        # [INFERENCE] classification (see module docstring above _AUDIO_MEDIA_TYPES) - log the raw
        # value so it's easy to grep production logs and confirm/deny the assumption post-deploy.
        logger.info("WhatsBotMais media message classified as %s (raw mediaType=%r)", media_kind, media_type)
        return ParsedInboundMessage(
            sender_number=sender_number,
            text=text,
            whatsbotmais_token=token,
            media_kind=media_kind,
            media_url=media_url,
        )

    if isinstance(media_type, str) and media_type in _UNSUPPORTED_MEDIA_TYPES:
        logger.info("WhatsBotMais media message ignored (unsupported mediaType=%r)", media_type)
        return None

    if isinstance(media_type, str) and media_type != "conversation":
        # Neither a known media kind nor a known "no reply pipeline" kind, e.g. a mediaType the
        # WhatsBotMais/Meta vocabulary added after this list was written. Falling through to plain
        # text handling below silently drops the actual media and replies only to any caption -
        # surface it loudly so this doesn't go unnoticed.
        logger.warning(
            "WhatsBotMais message has unrecognized mediaType=%r; falling back to text-only handling "
            "(caption present=%s)",
            media_type,
            bool(text.strip()),
        )

    if not text.strip():
        return None

    return ParsedInboundMessage(sender_number=sender_number, text=text, whatsbotmais_token=token)


def _parse_evolution_payload(payload: dict) -> ParsedInboundMessage | None:
    """Best-effort parse of a raw Evolution API `messages.upsert` webhook payload."""
    event = str(payload.get("event", "")).strip().lower().replace("_", ".")
    if event != "messages.upsert":
        return None

    data = payload.get("data")
    if not isinstance(data, dict):
        return None

    key = data.get("key") or {}
    if not isinstance(key, dict) or key.get("fromMe"):
        return None

    remote_jid = key.get("remoteJid")
    if not isinstance(remote_jid, str) or not remote_jid:
        return None
    sender_number = remote_jid.split("@", 1)[0]
    if not sender_number:
        return None

    message = data.get("message")
    if not isinstance(message, dict):
        return None
    text = message.get("conversation")
    if not text:
        extended = message.get("extendedTextMessage")
        if isinstance(extended, dict):
            text = extended.get("text")
    if not isinstance(text, str) or not text.strip():
        return None

    return ParsedInboundMessage(sender_number=sender_number, text=text)


def _parse_meta_payload(payload: dict) -> ParsedInboundMessage | None:
    """Best-effort parse of a native Meta WhatsApp Cloud API webhook payload (used when the
    instance is connected via the API Oficial provider directly, bypassing WhatsBotMais's own
    wrapped ticket shape)."""
    if payload.get("object") != "whatsapp_business_account":
        return None

    entries = payload.get("entry")
    if not isinstance(entries, list):
        return None

    # Meta can batch multiple entries/changes per webhook delivery - loop through all of them
    # and reply to the first actual inbound text message found; status-only deliveries are
    # skipped entirely (no ParsedInboundMessage to build for those).
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue

            messages = value.get("messages")
            if not isinstance(messages, list) or not messages:
                # No inbound messages here - likely a `statuses` (delivery/read receipt) update
                # for a message we sent; nothing to reply to, keep scanning other entries.
                continue

            message = messages[0]
            if not isinstance(message, dict):
                continue
            sender_number = message.get("from")
            if not isinstance(sender_number, str) or not sender_number:
                continue
            if message.get("type") != "text":
                continue
            text_body = message.get("text")
            text = text_body.get("body") if isinstance(text_body, dict) else None
            if not isinstance(text, str) or not text.strip():
                continue

            return ParsedInboundMessage(sender_number=sender_number, text=text)

    return None


def parse_inbound_message(payload: dict) -> ParsedInboundMessage | None:
    """
    Returns the parsed inbound customer message (text, audio, or image), or None if the payload
    doesn't match a message we can reply to (status update, unsupported media, echo of our own
    send, or an unrecognized shape).
    """
    return (
        _parse_whatsbotmais_payload(payload) or _parse_evolution_payload(payload) or _parse_meta_payload(payload)
    )
