import persona.api.app as app_module


def test_rate_window_rejects_then_recovers(monkeypatch):
    monkeypatch.setattr(app_module.config, "PUBLIC_RATE_LIMIT_PER_MINUTE", 2)
    app_module._RATE_WINDOWS.clear()
    assert app_module._allow_rate("u", 10)
    assert app_module._allow_rate("u", 11)
    assert not app_module._allow_rate("u", 12)
    assert app_module._allow_rate("u", 70)
