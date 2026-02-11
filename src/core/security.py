"""Utilidades de seguridad para webhooks."""

import hashlib
import hmac
import json


def generate_webhook_signature(payload: dict, secret: str) -> str:
    """Genera HMAC-SHA256 signature del payload para verificación."""
    payload_bytes = json.dumps(payload, sort_keys=True).encode()
    signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def verify_webhook_signature(payload: dict, signature: str, secret: str) -> bool:
    """Verifica la signature HMAC-SHA256 de un payload."""
    expected = generate_webhook_signature(payload, secret)
    return hmac.compare_digest(expected, signature)
