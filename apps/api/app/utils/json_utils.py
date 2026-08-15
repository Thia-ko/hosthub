import json
import re

_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def safe_parse_json(raw: str) -> dict | None:
    """Parses a JSON object string, tolerating models that wrap it in prose. Returns None
    instead of raising when the content isn't valid/extractable JSON."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        match = _JSON_OBJECT_RE.search(raw or "")
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def safe_parse_json_array(raw: str) -> list:
    """Parses a JSON array string (e.g. AttendantPattern.examples). Returns [] on failure or
    if the parsed value isn't a list."""
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []
