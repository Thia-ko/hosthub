import hashlib
import secrets

# Prefix makes a leaked key greppable/identifiable in logs; unrelated to the secret's entropy.
KEY_PREFIX = "hhk_"
_SECRET_BYTES = 32
# "hhk_" + 8 chars of the token - enough to tell keys apart in a list without exposing the secret.
_PREFIX_DISPLAY_LEN = 12

# Fixed set of permissions an API key can carry. Kept small and named after the capability it
# grants, not the endpoint/table behind it, so the contract stays stable if the implementation
# changes - same convention as app.services.outbound_webhooks.EVENTS.
PROMPT_READ = "prompt:read"
DATA_READ = "data:read"
MESSAGES_WRITE = "messages:write"

SCOPES = (PROMPT_READ, DATA_READ, MESSAGES_WRITE)

SCOPE_LABELS = {
    PROMPT_READ: "Ler o prompt ativo",
    DATA_READ: "Ler dados coletados pela IA",
    MESSAGES_WRITE: "Enviar mensagens no WhatsApp da instancia",
}


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_prefix, key_hash). `raw_key` is returned to the caller exactly
    once by the create endpoint; only `key_prefix` and `key_hash` are persisted (ApiKey)."""
    raw_key = f"{KEY_PREFIX}{secrets.token_urlsafe(_SECRET_BYTES)}"
    return raw_key, raw_key[:_PREFIX_DISPLAY_LEN], hash_api_key(raw_key)
