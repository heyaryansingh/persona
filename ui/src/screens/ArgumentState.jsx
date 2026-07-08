import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api.js";

// horizontal bar for a signed metric: centered at 0, fills left (negative) or right (positive)
function SignedBar({ label, value }) {
  const v = Number.isFinite(value) ? value : 0;
  const pct = Math.min(Math.abs(v) * 50, 50); // clamp so it never blows past the half-track
  return (
    <div style={{ marginBottom: 10 }}>
      <div className="spread mono" style={{ fontSize: 11, color: "var(--ink-soft)", marginBottom: 3 }}>
        <span>{label}</span>
        <span>{v.toFixed(3)}</span>
      </div>
      <div style={{ position: "relative", height: 6, background: "var(--paper-2)", border: "1px solid var(--rule)", borderRadius: 3 }}>
        <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "var(--rule)" }} />
        <div
          style={{
            position: "absolute",
            top: 0, bottom: 0,
            left: v >= 0 ? "50%" : `calc(50% - ${pct}%)`,
            width: `${pct}%`,
            background: v >= 0 ? "var(--live)" : "var(--human)",
            borderRadius: 3,
          }}
        />
      </div>
    </div>
  );
}

export default function ArgumentState() {
  const [beliefs, setBeliefs] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [argument, setArgument] = useState(null);
  const [error, setError] = useState(null);
  const [loadingArg, setLoadingArg] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.beliefs()
      .then((res) => {
        if (cancelled) return;
        const list = res?.beliefs || [];
        setBeliefs(list);
        if (list.length) setSelectedId(String(list[0].claim_id));
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoadingArg(true);
    api.argument(selectedId)
      .then((res) => !cancelled && setArgument(res))
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoadingArg(false));
    return () => { cancelled = true; };
  }, [selectedId]);

  if (error) {
    return (
      <div>
        <div className="screen-title">Argument State</div>
        <p className="muted">Could not load: {error}</p>
      </div>
    );
  }

  if (beliefs === null) {
    return (
      <div>
        <div className="screen-title">Argument State</div>
        <p className="muted">Loading beliefs…</p>
      </div>
    );
  }

  if (beliefs.length === 0) {
    return (
      <div>
        <div className="screen-title">Argument State</div>
        <p className="muted">No beliefs yet — nothing has been committed to the self.</p>
      </div>
    );
  }

  const selected = beliefs.find((b) => String(b.claim_id) === selectedId);
  const pct = selected ? Math.round((selected.calibrated_p ?? 0) * 100) : 0;

  return (
    <div>
      <div className="screen-title">Argument State</div>
      <p className="screen-lede">Where is this question heading?</p>

      <div style={{ marginBottom: 18 }}>
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="mono"
          style={{ width: "100%", padding: "8px 10px", background: "var(--card)", border: "1px solid var(--rule)", borderRadius: 6, color: "var(--ink)" }}
        >
          {beliefs.map((b) => (
            <option key={b.claim_id} value={b.claim_id}>{b.statement}</option>
          ))}
        </select>
      </div>

      {selected && (
        <div className="card" style={{ marginBottom: 14 }}>
          <p className="serif" style={{ fontSize: 18, margin: "0 0 10px" }}>{selected.statement}</p>
          <div className="row" style={{ marginBottom: 8 }}>
            <span className={`prov ${selected.provenance_state}`}>{selected.provenance_state}</span>
            {selected.anchor && <span className="chip human">anchored</span>}
          </div>
          <div className="spread mono" style={{ fontSize: 11, color: "var(--ink-soft)", marginBottom: 3 }}>
            <span>calibrated p</span><span>{pct}%</span>
          </div>
          <div className="pbar"><span style={{ width: `${pct}%` }} /></div>
        </div>
      )}

      <AnimatePresence mode="wait">
        {loadingArg || !argument ? (
          <motion.p key="loading" className="muted" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {loadingArg ? "Loading trajectory…" : "No trajectory data."}
          </motion.p>
        ) : (
          <motion.div
            key={selectedId}
            className="card"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="spread" style={{ marginBottom: 14 }}>
              <p className="serif" style={{ fontSize: 24, margin: 0 }}>{argument.state || "—"}</p>
              <span className="muted mono" style={{ fontSize: 11 }}>{argument.n_updates ?? 0} updates</span>
            </div>

            <SignedBar label="velocity" value={argument.velocity} />
            <SignedBar label="acceleration" value={argument.acceleration} />
            <SignedBar label="independence ratio" value={argument.independence_ratio} />

            <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px dotted var(--rule)" }}>
              <p className="muted mono" style={{ fontSize: 11, margin: 0 }}>
                forecast: {argument.forecast || "—"}
              </p>
              <p className="muted mono" style={{ fontSize: 10.5, margin: "4px 0 0" }}>
                descriptive only — not a prediction (E5 gate not passed)
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
