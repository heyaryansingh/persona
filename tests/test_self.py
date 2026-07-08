"""Living-doc Self tests (assert-based). Run: python tests/test_self.py

Core property (BUILD_PLAN acceptance §10.1): the self can be killed and re-hydrated
from its directory with NO belief loss, and hydrate() loads only the small core tier.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.self_state import Self  # noqa: E402
from persona.store import Claim       # noqa: E402


def test_kill_and_rehydrate_no_belief_loss():
    with tempfile.TemporaryDirectory() as d:
        me = Self(d)
        me.hydrate()
        me.add_belief(Claim("core1", "neuroinflammation drives AD", logit=2.0, tier="core"))
        me.add_belief(Claim("arch1", "obscure detail", logit=1.0, tier="archival"))
        me.store.human_confirm("core1", truth=1)     # anchor it
        me.notebook("noticed a contradiction between two well-powered studies")
        me.persist_core()
        me.close()

        # kill: drop the object entirely; reconstruct only from the directory
        del me
        revived = Self(d).hydrate()
        assert "core1" in revived.core, "core belief lost on rehydrate"
        c = revived.core["core1"]
        assert c.anchor and c.provenance_state == "HUMAN_CONFIRMED", "anchor/provenance lost"
        assert c.logit > 5, "confirmed logit lost"
        # archival is NOT loaded into context, but is still durably in the store
        assert "arch1" not in revived.core, "archival must not load into the core tier"
        assert revived.store.get_claim("arch1") is not None, "archival belief lost from store"
        revived.close()


def test_hydrate_loads_only_core():
    with tempfile.TemporaryDirectory() as d:
        me = Self(d)
        me.add_belief(Claim("k", "core", tier="core"))
        me.add_belief(Claim("a", "arch", tier="archival"))
        me.hydrate()
        assert set(me.core) == {"k"}
        me.close()


def test_notebook_and_beliefs_snapshot_are_readable():
    with tempfile.TemporaryDirectory() as d:
        me = Self(d)
        me.hydrate()
        me.add_belief(Claim("c", "a claim", logit=1.5, tier="core"))
        me.store.add_source("c", "PMID:1", "lab_A")
        me.notebook("spawned 8 readers; found 3 support / 1 contra")
        me.persist_core()
        nb = me.notebook_path.read_text(encoding="utf-8")
        assert "spawned 8 readers" in nb
        import json
        snap = json.loads(me.beliefs_path.read_text(encoding="utf-8"))
        assert snap[0]["claim_id"] == "c" and "calibrated_p" in snap[0]
        me.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} self tests passed.")
