import sqlite3

from cryptography.fernet import Fernet

from persona import provider_settings


def test_provider_keys_are_tenant_scoped_encrypted_and_revocable(monkeypatch, tmp_path):
    monkeypatch.setenv("PERSONA_PROVIDER_DB", str(tmp_path / "providers.db"))
    monkeypatch.setenv("PERSONA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(provider_settings, "preflight", lambda provider, key: None)

    provider_settings.save("alice", "openai", "sk-secret-value")
    assert provider_settings.configured("alice")[0]["provider"] == "openai"
    assert provider_settings.configured("bob") == []
    assert provider_settings.key_for("alice", "openai") == "sk-secret-value"
    db = sqlite3.connect(tmp_path / "providers.db")
    raw = db.execute("SELECT token FROM provider_keys").fetchone()[0]
    assert b"sk-secret-value" not in raw
    assert provider_settings.revoke("alice", "openai") is True
    assert provider_settings.key_for("alice", "openai") is None
