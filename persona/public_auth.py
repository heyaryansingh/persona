"""Minimal Google OIDC session boundary for the public Persona deployment.

The app owns a signed, HTTP-only session; Google only establishes identity.  Persona IDs
remain internal tenant resources and are checked by middleware before every route.
"""
from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode

import httpx
from itsdangerous import BadSignature, URLSafeTimedSerializer


_COOKIE = "persona_session"
_STATE = "persona_oauth_state"
_MAX_AGE = 60 * 60 * 12


def public_mode() -> bool:
    return os.environ.get("PERSONA_PUBLIC_MODE", "").lower() in {"1", "true", "yes", "on"}


def configured() -> bool:
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET")
                and os.environ.get("PERSONA_SESSION_SECRET"))


def _signer() -> URLSafeTimedSerializer:
    secret = os.environ.get("PERSONA_SESSION_SECRET")
    if not secret:
        raise RuntimeError("PERSONA_SESSION_SECRET is required in public mode")
    return URLSafeTimedSerializer(secret, salt="persona-session-v1")


def session_from(request):
    raw = request.cookies.get(_COOKIE)
    if not raw:
        return None
    try:
        data = _signer().loads(raw, max_age=_MAX_AGE)
        if not isinstance(data, dict) or not data.get("sub") or not data.get("csrf"):
            return None
        return data
    except (BadSignature, RuntimeError):
        return None


def login_url(request) -> tuple[str, str]:
    if not configured():
        raise RuntimeError("Google OAuth and session secret are required in public mode")
    state = secrets.token_urlsafe(32)
    redirect_uri = str(request.url_for("oauth_callback"))
    query = urlencode({"client_id": os.environ["GOOGLE_CLIENT_ID"], "redirect_uri": redirect_uri,
                       "response_type": "code", "scope": "openid email profile", "state": state,
                       "prompt": "select_account"})
    return f"https://accounts.google.com/o/oauth2/v2/auth?{query}", state


def exchange_code(request, code: str, state: str):
    expected = request.cookies.get(_STATE)
    if not expected or not secrets.compare_digest(expected, state):
        raise ValueError("invalid OAuth state")
    redirect_uri = str(request.url_for("oauth_callback"))
    response = httpx.post("https://oauth2.googleapis.com/token", data={
        "code": code, "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"], "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"}, timeout=10)
    response.raise_for_status()
    from google.oauth2 import id_token
    from google.auth.transport.requests import Request
    claims = id_token.verify_oauth2_token(response.json()["id_token"], Request(), os.environ["GOOGLE_CLIENT_ID"])
    if not claims.get("email_verified") or not claims.get("sub"):
        raise ValueError("Google account email is not verified")
    return {"sub": claims["sub"], "email": claims.get("email", ""), "csrf": secrets.token_urlsafe(32)}


def set_session(response, session: dict) -> None:
    secure = public_mode()
    response.set_cookie(_COOKIE, _signer().dumps(session), max_age=_MAX_AGE, httponly=True,
                        secure=secure, samesite="lax", path="/")


def set_state(response, state: str) -> None:
    response.set_cookie(_STATE, state, max_age=600, httponly=True, secure=public_mode(),
                        samesite="lax", path="/auth")


def clear_session(response) -> None:
    response.delete_cookie(_COOKIE, path="/")
    response.delete_cookie(_STATE, path="/auth")
