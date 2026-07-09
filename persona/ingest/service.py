"""Shared ingestion HTTP core (v5 P1) — the fix for "rate-limiting halts everything".

One process-wide service (shared across ALL personas so global API limits + cache are respected):
- persistent HTTP cache (hishel + SQLite): `reflect` re-issuing the same search is a CACHE HIT,
  not a new request — this alone stops the ~5s churn that burned the rate limit.
- per-host rate limiter (min interval + bounded concurrency) so bursts don't trip 429s.
- retry with exponential backoff + jitter that HONORS `Retry-After` on 429/503.
- sync (httpx.Client) to fit the reader's asyncio.to_thread worker model; thread-safe.

aiolimiter is async-only, so the per-host limiter here is a small sync token-gate (justified:
the read path is sync-in-threads). tenacity's wait can't read Retry-After off the response, so
the retry loop is explicit (~15 lines) and honors it directly.
"""
from __future__ import annotations

import random
import threading
import time
from pathlib import Path

import httpx

from .. import config

_UA = "persona-researcher/5.0 (mailto:persona-researcher@example.org)"
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


# polite defaults per host (OpenAlex polite pool ~10 rps; be conservative for unattended runs)
_LIMITS = {
    "api.openalex.org": (0.15, 4),
    "api.crossref.org": (0.25, 3),
    "export.arxiv.org": (0.4, 2),
    "www.ebi.ac.uk": (0.2, 3),
    "api.semanticscholar.org": (1.1, 1),     # S2 keyless is strict
    "_default": (0.3, 3),
}


class IngestService:
    def __init__(self, cache_dir: Path = None, max_retries: int = 4):
        cdir = Path(cache_dir or (config.ROOT / ".cache" / "http"))
        cdir.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self._limiters: dict[str, _HostLimiter] = {}
        self._llock = threading.Lock()
        try:
            import hishel
            storage = hishel.SQLiteStorage(ttl=7 * 24 * 3600,
                                           connection=__import__("sqlite3").connect(
                                               str(cdir / "hishel.db"), check_same_thread=False))
            self.client = hishel.CacheClient(storage=storage, timeout=30.0,
                                             headers={"User-Agent": _UA}, follow_redirects=True)
        except Exception:
            # cache optional — degrade to a plain client rather than fail ingestion
            self.client = httpx.Client(timeout=30.0, headers={"User-Agent": _UA},
                                       follow_redirects=True)

    def _limiter(self, host: str) -> _HostLimiter:
        with self._llock:
            lim = self._limiters.get(host)
            if lim is None:
                mi, mc = _LIMITS.get(host, _LIMITS["_default"])
                lim = self._limiters[host] = _HostLimiter(mi, mc)
            return lim

    def _request(self, method: str, url: str, **kw) -> httpx.Response:
        host = httpx.URL(url).host or "_default"
        lim = self._limiter(host)
        last_exc = None
        for attempt in range(self.max_retries + 1):
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
            if attempt >= self.max_retries:
                break
            delay = ra if ra is not None else min(20.0, (2 ** attempt) + random.uniform(0, 1.0))
            time.sleep(delay)
        if last_exc:
            raise last_exc
        raise httpx.HTTPStatusError("exhausted retries", request=None,
                                    response=r) if r is not None else RuntimeError("request failed")

    def get_json(self, url: str, params: dict = None) -> dict:
        return self._request("GET", url, params=params).json()

    def get_bytes(self, url: str, accept: str = None) -> bytes:
        headers = {"Accept": accept} if accept else None
        return self._request("GET", url, headers=headers).content

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
