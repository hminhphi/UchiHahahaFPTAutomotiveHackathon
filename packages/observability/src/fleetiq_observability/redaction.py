"""Recursive secret redaction for structured log values."""

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

_SENSITIVE_KEYS = frozenset(
    {
        "apikey",
        "authorization",
        "credential",
        "credentials",
        "password",
        "proxyauthorization",
        "secret",
        "secretkey",
        "token",
        "xapikey",
    }
)
_PRESIGNED_QUERY_KEYS = frozenset(
    {
        "awsaccesskeyid",
        "googleaccessid",
        "sig",
        "signature",
        "xamzcredential",
        "xamzsecuritytoken",
        "xamzsignature",
        "xgoogcredential",
        "xgoogsignature",
    }
)
_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


def _normalized_key(value: object) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def _redact_url_token(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.query:
        return value

    query_keys = {_normalized_key(key) for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if not query_keys.intersection(_PRESIGNED_QUERY_KEYS):
        return value
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, REDACTED, parsed.fragment))


def _redact_urls(value: str) -> str:
    return _URL_PATTERN.sub(lambda match: _redact_url_token(match.group(0)), value)


def redact(value: Any) -> Any:
    """Return a recursively redacted copy suitable for logging."""
    if isinstance(value, Mapping):
        redacted: dict[object, Any] = {}
        for key, item in value.items():
            if _normalized_key(key) in _SENSITIVE_KEYS:
                redacted[key] = REDACTED
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    if isinstance(value, str):
        return _redact_urls(value)
    return value
