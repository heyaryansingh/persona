"""Shared ingestion HTTP core (v5 P1) — the fix for "rate-limiting halts everything".

One process-wide service (shared across ALL personas so global API limits + cache are respected):
- persistent HTTP cache (stdlib sqlite3, keyed TTL): `reflect` re-issuing the same search is a
  CACHE HIT, not a new request — this alone stops the ~5s churn that burned the rate limit, and it
  keeps restarts during development from re-spending the daily API budget.
- per-host rate limiter (min interval + bounded concurrency), tuned to each API's CURRENT documented
  limits (see `_LIMITS`), so bursts don't trip 429s.
- retry with exponential backoff + jitter that HONORS `Retry-After` on 429/503, failing over fast on
  a long ban so the daemon never hangs.
- sync (httpx.Client) to fit the reader's asyncio.to_thread worker model; thread-safe.

The cache is a small keyed TTL store (not a full RFC-9111 cache): our requests are idempotent GETs
to search/PDF endpoints, so "same query within N days -> don't refetch" is exactly right and avoids
coupling to hishel's shifting API (1.3 removed its drop-in client).
"""
from __future__ import annotations

import json
import random
import sqlite3
import threading
import time
from pathlib import Path

import httpx

from .. import config

# Real contact email -> Crossref polite pool (email-before-block) + OpenAlex identification.
_UA = f"persona-researcher/5.0 (mailto:{config.CONTACT_EMAIL})"
_RETRY_STATUS = {429, 500, 502, 503, 504}


class _HostLimiter:
    """Per-host: enforce a minimum spacing between requests + a max in-flight cap."""
    def __init__(self, min_interval: float, max_concurrent: int):
        self.min_interval = min_interval
        self.sem = threading.Semaphore(max_concurrent)
        self._lock = threading.Lock()
        self._next = 0.0

    def acquire(self):
        self.sem.acquire()
        with self._lock:
            wait = self._next - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._next = time.monotonic() + self.min_interval

    def release(self):
        self.sem.release()


# Per-host (min_interval_seconds, max_concurrent), VERIFIED against each API's current docs
# (2026-07; see the rate-limit verification workflow). Chosen to stay safely under the real limit:
#   openalex : 100 rps ceiling; real constraint is a daily $-budget -> api_key (10x) + the HTTP
#              cache do the heavy lifting. 0.15s/3 ~= 20 rps, far under 100.
#   crossref : Dec-2025 change made list/query limits pool-specific — keyless is 1 rps/1! The mailto
#              polite pool raises it to 3 rps/3. We send mailto (below) + hold 0.5s/2 (2 rps).
#   arxiv    : Terms of Use = 1 request / 3 seconds, single connection. Was 0.4s/2 (a violation).
#   europepmc: 10 rps per IP, no key/polite tier. 0.5s/1 = 2 rps, comfortably under.
#   ncbi     : eutils = 3 rps keyless, 10 rps with api_key. 0.4s/1 keyless-safe.
_LIMITS = {
    "api.openalex.org": (0.15, 3),
    "api.crossref.org": (0.5, 2),
    "export.arxiv.org": (3.2, 1),
    "www.ebi.ac.uk": (0.5, 1),
    "eutils.ncbi.nlm.nih.gov": (0.4, 1),
    "_default": (0.5, 2),
}


class _TTLCache:
    """Tiny stdlib SQLite cache for idempotent GETs (search JSON, PDFs). Our need is narrow —
    "same query within N days -> don't refetch" — so a keyed TTL store beats a full RFC-9111 cache
    (hishel 1.3 dropped its drop-in CacheClient; this removes that version coupling entirely).
    This is THE thing that stops re-scouts from burning the daily API budget, so it must not break."""
    def __init__(self, path: Path, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, ts REAL, body BLOB)")
        self.db.commit()

    def get(self, key: str) -> bytes | None:
        with self._lock:
            row = self.db.execute("SELECT ts, body FROM cache WHERE k=?", (key,)).fetchone()
        if row and (time.time() - row[0]) < self.ttl:
            return row[1]
        return None

    def put(self, key: str, body: bytes) -> None:
        with self._lock:
            self.db.execute("INSERT OR REPLACE INTO cache (k, ts, body) VALUES (?,?,?)",
                            (key, time.time(), body))
            self.db.commit()


def _ckey(url: str, params: dict | None, accept: str | None) -> str:
    return json.dumps(["GET", url, params or {}, accept], sort_keys=True, default=str)


class IngestService:
    def __init__(self, cache_dir: Path = None, max_retries: int = 4):
        cdir = Path(cache_dir or (config.ROOT / ".cache" / "http"))
        cdir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self._limiters: dict[str, _HostLimiter] = {}
        self._llock = threading.Lock()
        self.client = httpx.Client(timeout=30.0, headers={"User-Agent": _UA}, follow_redirects=True)
        try:
            self.cache = _TTLCache(cdir / "cache.db", config.HTTP_CACHE_TTL_DAYS * 86400)
        except Exception as e:                       # cache optional, but WARN — it guards the budget
            import sys
            print(f"[ingest] WARNING: HTTP cache disabled ({e!r}); repeated searches will hit the "
                  f"network and count against rate/daily limits.", file=sys.stderr)
            self.cache = None

    def _limiter(self, host: str) -> _HostLimiter:
        with self._llock:
            lim = self._limiters.get(host)
            if lim is None:
                mi, mc = _LIMITS.get(host, _LIMITS["_default"])
                lim = self._limiters[host] = _HostLimiter(mi * config.INGEST_INTERVAL_MULT, mc)
            return lim

    def _request(self, method: str, url: str, **kw) -> httpx.Response:
        host = httpx.URL(url).host or "_default"
        lim = self._limiter(host)
        max_retries = kw.pop("_retries", None)
        if max_retries is None:
            max_retries = self.max_retries
        last_exc = None
        for attempt in range(max_retries + 1):
            lim.acquire()
            try:
                r = self.client.request(method, url, **kw)
            except httpx.TransportError as e:
                last_exc = e
                r = None
            finally:
                lim.release()
            if r is not None and r.status_code not in _RETRY_STATUS:
                r.raise_for_status()
                return r
            # honor Retry-After, but if the host wants us gone for a long time (e.g. a daily
            # ban with Retry-After in the thousands of seconds), DON'T sleep — raise so the caller
            # fails over to another source immediately. This is what stops the daemon hanging.
            ra = None
            if r is not None:
                rah = r.headers.get("Retry-After")
                if rah and rah.isdigit():
                    ra = float(rah)
            if ra is not None and ra > 30:
                raise httpx.HTTPStatusError(f"rate-limited, Retry-After={ra:.0f}s (fail over)",
                                            request=r.request, response=r)
            if attempt >= max_retries:
                break
            delay = ra if ra is not None else min(8.0, (2 ** attempt) + random.uniform(0, 1.0))
            time.sleep(delay)
        if last_exc:
            raise last_exc
        raise httpx.HTTPStatusError("exhausted retries", request=None,
                                    response=r) if r is not None else RuntimeError("request failed")

    def get_json(self, url: str, params: dict = None, retries: int = None, timeout: float = None) -> dict:
        key = _ckey(url, params, None)
        if self.cache and (hit := self.cache.get(key)) is not None:
            return json.loads(hit)
        kw = {"params": params, "_retries": retries}
        if timeout is not None:
            kw["timeout"] = timeout
        body = self._request("GET", url, **kw).content
        if self.cache:
            self.cache.put(key, body)
        return json.loads(body)

    def post_json(self, url: str, body: dict, retries: int = None, timeout: float = None) -> dict:
        """POST a JSON body (e.g. a GraphQL query), cached by url+body. Rate-limited + retried."""
        key = _ckey(url, body, "POST")
        if self.cache and (hit := self.cache.get(key)) is not None:
            return json.loads(hit)
        kw = {"json": body, "_retries": retries}
        if timeout is not None:
            kw["timeout"] = timeout
        content = self._request("POST", url, **kw).content
        if self.cache:
            self.cache.put(key, content)
        return json.loads(content)

    def get_bytes(self, url: str, accept: str = None) -> bytes:
        key = _ckey(url, None, accept)
        if self.cache and (hit := self.cache.get(key)) is not None:
            return hit
        headers = {"Accept": accept} if accept else None
        body = self._request("GET", url, headers=headers).content
        if self.cache:
            self.cache.put(key, body)
        return body

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass


_SERVICE: IngestService | None = None
_SLOCK = threading.Lock()


def service() -> IngestService:
    global _SERVICE
    if _SERVICE is None:
        with _SLOCK:
            if _SERVICE is None:
                _SERVICE = IngestService()
    return _SERVICE


def _selfcheck() -> None:
    """Network-free checks on the load-bearing bits: the TTL cache and the verified limits."""
    import tempfile
    # cache: put -> hit; expired -> miss
    c = _TTLCache(Path(tempfile.mkdtemp()) / "c.db", ttl_seconds=100)
    c.put("k", b"v"); assert c.get("k") == b"v", "cache miss after put"
    c.ttl = -1; assert c.get("k") is None, "expired entry still served"
    # key determinism regardless of param order
    assert _ckey("u", {"a": 1, "b": 2}, None) == _ckey("u", {"b": 2, "a": 1}, None)
    # arXiv TOU is 1 req / 3s — this MUST stay >=3s or arXiv blocks the IP
    assert _LIMITS["export.arxiv.org"][0] >= 3.0, "arXiv interval violates the 1-req/3s TOU"
    assert _LIMITS["export.arxiv.org"][1] == 1, "arXiv allows a single connection only"
    print("service self-check OK: cache put/hit/expire, key-order stable, arXiv >=3s/1-conn")


if __name__ == "__main__":
    _selfcheck()
