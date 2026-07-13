import importlib

from persona import config


def test_unlimited_spend_raises_only_the_implicit_worker_default(monkeypatch):
    monkeypatch.setenv("PERSONA_UNLIMITED_SPEND", "1")
    monkeypatch.delenv("PERSONA_DAILY_BUDGET_USD", raising=False)
    monkeypatch.delenv("PERSONA_WORKERS", raising=False)
    cfg = importlib.reload(config)
    assert cfg.UNLIMITED_SPEND is True
    assert cfg.N_WORKERS == 8
    assert cfg.DAILY_BUDGET_USD == float("inf")

    monkeypatch.setenv("PERSONA_DAILY_BUDGET_USD", "20")
    cfg = importlib.reload(config)
    assert cfg.UNLIMITED_SPEND is False
    assert cfg.N_WORKERS == 3
    assert cfg.DAILY_BUDGET_USD == 20

    monkeypatch.setenv("PERSONA_WORKERS", "12")
    cfg = importlib.reload(config)
    assert cfg.N_WORKERS == 12

    monkeypatch.delenv("PERSONA_UNLIMITED_SPEND", raising=False)
    monkeypatch.delenv("PERSONA_DAILY_BUDGET_USD", raising=False)
    monkeypatch.delenv("PERSONA_WORKERS", raising=False)
    importlib.reload(config)
