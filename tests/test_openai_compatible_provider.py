from types import SimpleNamespace

import pytest

from persona import providers


def test_openai_compatible_adapter_uses_explicit_provider_model(monkeypatch):
    seen = {}
    def post(url, **kwargs):
        seen.update(url=url, **kwargs)
        return SimpleNamespace(status_code=200, json=lambda: {"choices": [{"message": {"content": "grounded"}}], "usage": {"total_tokens": 9}})
    monkeypatch.setattr("httpx.post", post)
    result = providers.openai_compatible_chat("huggingface", "secret", "org/model", [{"role": "user", "content": "hi"}])
    assert result == {"provider": "huggingface", "model": "org/model", "text": "grounded", "usage": {"total_tokens": 9}}
    assert seen["url"] == "https://router.huggingface.co/v1/chat/completions"
    assert seen["json"]["model"] == "org/model"


def test_openai_compatible_adapter_rejects_implicit_fallback():
    with pytest.raises(providers.ProviderError):
        providers.openai_compatible_chat("anthropic", "secret", "x", [])
