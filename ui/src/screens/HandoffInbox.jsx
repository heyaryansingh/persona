import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "../api.js";

// kind string -> badge class; anything unrecognized falls back to no-evidence styling
const badgeClass = (kind) => {
  if (kind === "true-refutation" || kind === "context-divergence" || kind === "no-evidence") return kind;
  return "no-evidence";
};

function HandoffCard({ h, onResolved }) {
  const [picked, setPicked] = useState(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState(null);
  const [anchored, setAnchored] = useState(null); // set after successful resolve

  const runSelfTest = async () => {
    setTesting(true);
    setError(null);
    try {
      const r = await api.selftest(h.claim_key);
      setTestResult(r);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setTesting(false);
    }
  };

  const resolve = async (truth) => {
    if (!picked) return;
    setResolving(true);
    setError(null);
    try {
      const r = await api.resolve(h.claim_key, picked, truth);
      setAnchored(r);
      setTimeout(() => onResolved(h.claim_key), 900);
    } catch (e) {
      setError(String(e.message || e));
      setResolving(false);
    }
  };

  return (
    <motion.div
      className="card"
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: 40 }}
      transition={{ duration: 0.35 }}
    >
      <div className="spread">
        <span className={"badge " + badgeClass(h.kind)}>{h.kind}</span>
        <span className="muted mono" style={{ fontSize: 11 }}>{h.status}</span>
      </div>
      <p className="serif" style={{ margin: "10px 0" }}>{h.question}</p>
      <div className="row muted mono" style={{ fontSize: 12, marginBottom: 10 }}>
        <span>support: {(h.support || []).length}</span>
        <span>·</span>
        <span>refute: {(h.refute || []).length}</span>
      </div>

      {anchored ? (
        <div className="row" style={{ gap: 8 }}>
          <span className="prov HUMAN_CONFIRMED">HUMAN_CONFIRMED</span>
          <span className="muted mono" style={{ fontSize: 12 }}>anchored — belief locked in</span>
        </div>
      ) : (
        <>
          <div className="grid" style={{ gap: 6, marginBottom: 12 }}>
            {(h.candidate_explanations || []).map((exp, i) => (
              <label key={i} className="row mono" style={{ fontSize: 12.5, cursor: "pointer" }}>
                <input
                  type="radio"
                  name={h.claim_key}
                  checked={picked === exp}
                  onChange={() => setPicked(exp)}
                />
                {exp}
              </label>
            ))}
            {(!h.candidate_explanations || h.candidate_explanations.length === 0) && (
              <span className="muted mono" style={{ fontSize: 12 }}>no candidate explanations offered</span>
            )}
          </div>

          <div className="spread">
            <button className="action ghost" onClick={runSelfTest} disabled={testing}>
              {testing ? "running…" : "Run self-test"}
            </button>
            <div className="row" style={{ gap: 8 }}>
              <button className="action ghost" disabled={!picked || resolving} onClick={() => resolve(1)}>
                Holds ✓
              </button>
              <button className="action ghost" disabled={!picked || resolving} onClick={() => resolve(0)}>
                Refuted ✗
              </button>
            </div>
          </div>

          {testResult && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mono"
              style={{ fontSize: 11.5, marginTop: 10, borderTop: "1px dotted var(--rule)", paddingTop: 8 }}
            >
              outcome: <strong>{String(testResult.outcome)}</strong> · confidence: {testResult.confidence}
              {testResult.dataset && ` · dataset: ${testResult.dataset.accession} (${testResult.dataset.source})`}
              {testResult.is_replay && (
                <span className="chip human" style={{ marginLeft: 8 }}>replay — first-pass only, sign-off still required</span>
              )}
            </motion.div>
          )}

          {error && <div className="mono" style={{ fontSize: 11.5, color: "var(--human)", marginTop: 8 }}>{error}</div>}
        </>
      )}
    </motion.div>
  );
}

export default function HandoffInbox() {
  const [state, setState] = useState({ loading: true, error: null, handoffs: [] });

  useEffect(() => {
    let live = true;
    api.handoffs()
      .then((r) => live && setState({ loading: false, error: null, handoffs: r.handoffs || [] }))
      .catch((e) => live && setState({ loading: false, error: String(e.message || e), handoffs: [] }));
    return () => { live = false; };
  }, []);

  const dismiss = (key) => {
    setState((s) => ({ ...s, handoffs: s.handoffs.filter((h) => h.claim_key !== key) }));
  };

  return (
    <div>
      <div className="screen-title">Human Handoff</div>
      <div className="screen-lede">What needs my judgment</div>

      {state.loading && <div className="muted mono">loading…</div>}
      {state.error && <div className="mono" style={{ color: "var(--human)" }}>{state.error}</div>}
      {!state.loading && !state.error && state.handoffs.length === 0 && (
        <div className="muted mono">No open judgment calls.</div>
      )}

      <div className="grid cols-2">
        <AnimatePresence>
          {state.handoffs.map((h) => (
            <HandoffCard key={h.claim_key} h={h} onResolved={dismiss} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
