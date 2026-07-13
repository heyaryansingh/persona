"""Encrypted, tenant-scoped provider credentials. Plaintext never leaves this module."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cryptography.fernet import Fernet, InvalidToken


_PROVIDERS = {
    "anthropic": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
    "huggingface": "https://router.huggingface.co/v1/models",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fernet() -> Fernet:
    key = os.environ.get("PERSONA_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("PERSONA_ENCRYPTION_KEY is required for provider settings")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError("PERSONA_ENCRYPTION_KEY must be a Fernet key") from exc


def _db():
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgres"):
        import psycopg
        db = psycopg.connect(url)
        db.execute("CREATE TABLE IF NOT EXISTS provider_keys (owner_id TEXT NOT NULL, provider TEXT NOT NULL, token BYTEA NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(owner_id, provider))")
        db.execute("CREATE TABLE IF NOT EXISTS provider_audit (owner_id TEXT NOT NULL, provider TEXT NOT NULL, action TEXT NOT NULL, at TEXT NOT NULL)")
        return db
    path = Path(os.environ.get("PERSONA_PROVIDER_DB", Path.cwd() / ".persona-providers.db"))
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS provider_keys (owner_id TEXT NOT NULL, provider TEXT NOT NULL, token BLOB NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(owner_id, provider))")
    db.execute("CREATE TABLE IF NOT EXISTS provider_audit (owner_id TEXT NOT NULL, provider TEXT NOT NULL, action TEXT NOT NULL, at TEXT NOT NULL)")
    return db


def _execute(db, sql: str, params=()):
    """Keep local SQLite tests and production psycopg parameter styles identical."""
    if db.__class__.__module__.startswith("psycopg"):
        sql = sql.replace("?", "%s")
    return db.execute(sql, params)


def _audit(db, owner_id: str, provider: str, action: str) -> None:
    _execute(db, "INSERT INTO provider_audit VALUES (?,?,?,?)", (owner_id, provider, action, _now()))


def _check_provider(provider: str) -> str:
    if provider not in _PROVIDERS:
        raise ValueError("unsupported provider")
    return provider


def preflight(provider: str, key: str) -> None:
    """Non-generative token check; no prompt/completion is sent or stored."""
    provider = _check_provider(provider)
    if not isinstance(key, str) or len(key.strip()) < 8:
        raise ValueError("invalid provider key")
    headers = {"Authorization": f"Bearer {key.strip()}"}
    if provider == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
    response = httpx.get(_PROVIDERS[provider], headers=headers, timeout=10)
    if response.status_code >= 400:
        raise ValueError("provider rejected key")


def save(owner_id: str, provider: str, key: str) -> None:
    provider = _check_provider(provider)
    token = _fernet().encrypt(key.strip().encode())
    with _db() as db:
        _execute(db, "INSERT INTO provider_keys(owner_id,provider,token,updated_at) VALUES (?,?,?,?) ON CONFLICT(owner_id,provider) DO UPDATE SET token=excluded.token,updated_at=excluded.updated_at", (owner_id, provider, token, _now()))
        _audit(db, owner_id, provider, "rotated")


def configured(owner_id: str) -> list[dict]:
    with _db() as db:
        rows = _execute(db, "SELECT provider,updated_at FROM provider_keys WHERE owner_id=? ORDER BY provider", (owner_id,)).fetchall()
    return [{"provider": p, "configured": True, "updated_at": at} for p, at in rows]


def revoke(owner_id: str, provider: str) -> bool:
    provider = _check_provider(provider)
    with _db() as db:
        cur = _execute(db, "DELETE FROM provider_keys WHERE owner_id=? AND provider=?", (owner_id, provider))
        _audit(db, owner_id, provider, "revoked")
    return bool(cur.rowcount)


def key_for(owner_id: str, provider: str) -> str | None:
    provider = _check_provider(provider)
    with _db() as db:
        row = _execute(db, "SELECT token FROM provider_keys WHERE owner_id=? AND provider=?", (owner_id, provider)).fetchone()
    if not row:
        return None
    try:
        return _fernet().decrypt(row[0]).decode()
    except InvalidToken as exc:
        raise RuntimeError("provider credential cannot be decrypted") from exc
