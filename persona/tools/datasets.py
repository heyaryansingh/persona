"""Dataset fetch (v4 P5) — pull a REAL dataset to disk so the sandbox can compute on it.

Egress is the safety boundary: fetching is allowed only from a curated allowlist of open-data
hosts, capped in size. The sandbox itself has NO network, so data must be fetched here (outside)
and mounted in. No arbitrary outbound requests, no irreversible actions.
"""
from __future__ import annotations

import urllib.parse
from pathlib import Path

# open-data / research-data hosts only
_ALLOW = (
    "raw.githubusercontent.com", "gist.githubusercontent.com", "objects.githubusercontent.com",
    "zenodo.org", "figshare.com", "ndownloader.figshare.com",
    "ftp.ncbi.nlm.nih.gov", "eutils.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov",
    "ftp.ebi.ac.uk", "www.ebi.ac.uk", "rest.ensembl.org",
    "archive.ics.uci.edu", "openml.org", "www.openml.org", "api.openml.org",
    "data.cityofnewyork.us", "raw.githack.com", "huggingface.co", "datasets-server.huggingface.co",
)
_MAX_BYTES = 30 * 1024 * 1024


def allowed(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in _ALLOW)


def fetch(url: str, dest_dir: Path, filename: str = None) -> dict:
    """Download `url` (allowlisted, size-capped) into dest_dir. Returns {ok, path, bytes} or error."""
    if not allowed(url):
        return {"ok": False, "error": f"host not in the open-data allowlist: "
                f"{urllib.parse.urlparse(url).netloc}"}
    import httpx
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = filename or (urllib.parse.urlparse(url).path.rsplit("/", 1)[-1] or "dataset.bin")
    name = "".join(c for c in name if c.isalnum() or c in "._-")[:80] or "dataset.bin"
    path = dest_dir / name
    from .. import config
    host = urllib.parse.urlparse(url).netloc.lower()
    if config.NCBI_API_KEY and host.endswith("ncbi.nlm.nih.gov") and "api_key=" not in url:
        url += ("&" if "?" in url else "?") + "api_key=" + config.NCBI_API_KEY   # 10 rps vs 3 keyless
    try:
        total = 0
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0,
                          headers={"User-Agent": f"persona-researcher/5.0 (mailto:{config.CONTACT_EMAIL})"}) as r:
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_bytes(65536):
                    total += len(chunk)
                    if total > _MAX_BYTES:
                        f.close(); path.unlink(missing_ok=True)
                        return {"ok": False, "error": f"dataset exceeds {_MAX_BYTES // (1024*1024)}MB cap"}
                    f.write(chunk)
        return {"ok": True, "path": str(path), "rel": name, "bytes": total}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
