"""Provider boundary: only this module resolves a tenant credential for an outbound model call."""
from __future__ import annotations

from . import config, public_auth


class ProviderError(RuntimeError):
    """A redacted, normalized provider failure safe to return to the UI/log."""


_OPENAI_COMPATIBLE = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "huggingface": "https://router.huggingface.co/v1/chat/completions",
}


def anthropic_client():
    from anthropic import Anthropic
    if public_auth.public_mode():
        from .context import get_persona
        from .provider_settings import key_for
        owner = get_persona().owner_id
        if not owner:
            raise RuntimeError("public persona has no tenant owner")
        key = key_for(owner, "anthropic")
        if not key:
            raise RuntimeError("Anthropic provider is not configured")
        return Anthropic(api_key=key)
    return Anthropic(api_key=config.ANTHROPIC_API_KEY)


def openai_compatible_chat(provider: str, key: str, model: str, messages: list[dict], *,
                           max_tokens: int = 512) -> dict:
    """One explicit OpenAI-compatible request; no provider/model fallback is permitted."""
    import httpx
    if provider not in _OPENAI_COMPATIBLE:
        raise ProviderError("provider is not OpenAI-compatible")
    if not model or not isinstance(messages, list):
        raise ProviderError("model and messages are required")
    try:
        response = httpx.post(_OPENAI_COMPATIBLE[provider], headers={"Authorization": f"Bearer {key}"},
                              json={"model": model, "messages": messages, "max_tokens": max_tokens}, timeout=60)
    except httpx.HTTPError as exc:
        raise ProviderError("provider unavailable") from exc
    if response.status_code >= 400:
        raise ProviderError("provider request rejected")
    try:
        data = response.json()
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("provider returned an invalid response") from exc
    return {"provider": provider, "model": model, "text": text, "usage": data.get("usage") or {}}
