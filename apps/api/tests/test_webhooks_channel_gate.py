"""Unit tests for app.api.v1.routers.webhooks._channel_is_ready.

Regression coverage for a real bug: the gate used to check only `Instance.whatsapp_instance_name`
(Evolution API's static connection name) before letting the auto-reply pipeline run. WhatsBotMais
connections never set that field - the reply token arrives on every inbound message instead (see
ParsedInboundMessage.whatsbotmais_token) - so a WhatsBotMais-only instance would silently never
auto-reply, even with a fully configured prompt and AI provider.
"""

from types import SimpleNamespace

from app.api.v1.routers.webhooks import _channel_is_ready
from app.models.instance import InstanceStatus
from app.services.whatsapp_channel import ParsedInboundMessage


def _instance(status=InstanceStatus.ACTIVE, whatsapp_instance_name=None):
    return SimpleNamespace(
        status=status,
        whatsapp_instance_name=whatsapp_instance_name,
        whatsapp_provider=None,
        meta_phone_number_id=None,
        meta_access_token=None,
    )


def _parsed(whatsbotmais_token=None):
    return ParsedInboundMessage(sender_number="5511999998888", text="oi", whatsbotmais_token=whatsbotmais_token)


def test_whatsbotmais_only_instance_is_ready_via_per_message_token():
    instance = _instance(whatsapp_instance_name=None)
    parsed = _parsed(whatsbotmais_token="tok-from-webhook")

    assert _channel_is_ready(instance, parsed) is True


def test_evolution_instance_is_ready_via_static_connection_name():
    instance = _instance(whatsapp_instance_name="evo-connection")
    parsed = _parsed(whatsbotmais_token=None)

    assert _channel_is_ready(instance, parsed) is True


def test_no_channel_at_all_is_not_ready():
    instance = _instance(whatsapp_instance_name=None)
    parsed = _parsed(whatsbotmais_token=None)

    assert _channel_is_ready(instance, parsed) is False


def test_paused_or_archived_instance_is_never_ready_even_with_a_valid_token():
    instance = _instance(status=InstanceStatus.PAUSED, whatsapp_instance_name="evo-connection")
    parsed = _parsed(whatsbotmais_token="tok-from-webhook")

    assert _channel_is_ready(instance, parsed) is False
