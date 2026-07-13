"""H1 (run_shell cwd jail) + M1 (clone SSRF) security regressions — Lane 4 / S3.
Root-cause guards in persona.api.app; see S0 board 2026-07-12 H1/M1."""
import pytest

from persona.paths import Paths
from persona.api.app import _jail_shell_cwd, _GIT_URL_RE, _SHELL_SCRATCH


def _paths(tmp_path):
    p = Paths(tmp_path)
    p.ensure()
    return p


# ---- H1: run_shell may never cwd into the durable self / knowledge dirs -----
@pytest.mark.parametrize("bad", [
    "self", "notes", "sources", "drafts", "projects", "deliverables",
    "investigations", ".persona",            # protected dirs
    "self/beliefs.md", "notes/x",            # nested into protected
    "..", ".", "", "../self", "../../etc",   # escape / root
])
def test_shell_cwd_refuses_protected(tmp_path, bad):
    with pytest.raises(ValueError):
        _jail_shell_cwd(_paths(tmp_path), bad)


@pytest.mark.parametrize("ok", ["code", "repos", "uploads", "runs", "datasets",
                                "repos/myrepo", "code/run", "datasets/geo"])
def test_shell_cwd_allows_scratch(tmp_path, ok):
    p = _paths(tmp_path)
    wd = _jail_shell_cwd(p, ok)
    assert wd.relative_to(p.workspace.resolve()).parts[0] in _SHELL_SCRATCH


# ---- M1: clone_repo host allowlist — no SSRF / internal / metadata ----------
@pytest.mark.parametrize("bad", [
    "https://169.254.169.254/a/b",           # cloud metadata
    "https://metadata.google.internal/x/y",
    "https://localhost/a/b", "https://127.0.0.1/a/b",
    "https://internal.evil.com/a/b",         # arbitrary host (old catch-all)
    "http://github.com/a/b",                 # non-https
    "file:///etc/passwd", "ssh://github.com/a/b",
    "https://github.com.evil.com/a/b",       # look-alike host
])
def test_clone_url_rejects(bad):
    assert not _GIT_URL_RE.match(bad), bad


@pytest.mark.parametrize("ok", [
    "https://github.com/psf/requests",
    "https://gitlab.com/group/proj",
    "https://bitbucket.org/team/repo",
])
def test_clone_url_accepts_known_hosts(ok):
    assert _GIT_URL_RE.match(ok), ok
