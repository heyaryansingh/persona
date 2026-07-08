import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api.js";

// Parses a notebook line like: - `2026-07-08T..Z` read 8 on "..." -> 20 candidates
function parseLine(line) {
  const m = line.match(/`([^`]+)`\s*(.*)$/);
  const warn = line.includes("⚠");
  if (!m) return { ts: "", rest: line, warn };
  return { ts: m[1], rest: m[2], warn };
}

const ATTENTION_FIELDS = [
  ["docs_read", "docs read"],
  ["candidates", "candidates"],
  ["committed", "committed"],
  ["held", "held"],
  ["contradictions", "contradictions"],
];

export default function Dashboard() {
  const [dash, setDash] = useState(null);
  const [lines, setLines] = useState([]);
  const [err, setErr] = useState(null);
  const [ticking, setTicking] = useState(false);
  const [pulse, setPulse] = useState(0);

  const load = useCallback(async () => {
    try {
      const [d, nb] = await Promise.all([api.dashboard(), api.notebook(6)]);
      setDash(d);
      setLines(nb.lines || []);
      setErr(null);
    } catch (e) {
      setErr(e.message || "failed to load");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const onTick = async () => {
    setTicking(true);
    try {
      await api.tick();
      await load();
      setPulse((p) => p + 1);
    } catch (e) {
      setErr(e.message || "tick failed");
    } finally {
      setTicking(false);
    }
  };

  if (err) {
    return (
      <div>
        <div className="screen-title">Dashboard</div>
        <p className="muted">Could not load the researcher: {err}</p>
      </div>
    );
  }

  if (!dash) {
    return (
      <div>
        <div className="screen-title">Dashboard</div>
        <p className="muted">Waking up…</p>
      </div>
    );
  }

  const att = dash.attention || {};
  const maxAtt = Math.max(1, ...ATTENTION_FIELDS.map(([k]) => att[k] || 0));

  return (
    <div>
      <div className="screen-title">Dashboard</div>
      <div className="spread" style={{ marginBottom: 6 }}>
        <h1 className="screen-lede" style={{ margin: 0 }}>{dash.name}</h1>
        <div className="row">
          <span className="chip live">{dash.disposition}</span>
          <span className="chip">{dash.n_beliefs} beliefs</span>
          {dash.n_open_handoffs > 0 && (
            <span className="chip human">{dash.n_open_handoffs} open handoffs</span>
          )}
        </div>
      </div>

      <div className="grid cols-2" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="screen-title" style={{ marginBottom: 10 }}>Interests</div>
          <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
            {(dash.interests || []).map((it) => (
              <span
                key={it.name}
                className="chip"
                title={it.reason}
                style={{ fontSize: 11 + Math.round((it.weight || 0) * 6) }}
              >
                {it.name}
              </span>
            ))}
            {(!dash.interests || dash.interests.length === 0) && (
              <span className="muted">no interests yet</span>
            )}
          </div>
        </div>

        <div className="card">
          <div className="screen-title" style={{ marginBottom: 10 }}>Agenda</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {(dash.agenda || []).slice(0, 6).map((a, i) => (
              <div key={i} className="row" style={{ alignItems: "flex-start" }}>
                <span className="chip">{a.kind}</span>
                <span className="mono" style={{ fontSize: 12.5 }}>{a.target}</span>
                <span className="muted" style={{ fontSize: 12 }}>— {a.why}</span>
              </div>
            ))}
            {(!dash.agenda || dash.agenda.length === 0) && (
              <span className="muted">agenda is empty</span>
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="screen-title" style={{ marginBottom: 10 }}>Attention</div>
        <div className="grid cols-3" style={{ gap: 12 }}>
          {ATTENTION_FIELDS.map(([k, label]) => (
            <div key={k}>
              <div className="spread">
                <span className="muted" style={{ fontSize: 11 }}>{label}</span>
                <span className="mono" style={{ fontSize: 15, fontWeight: 600 }}>{att[k] ?? 0}</span>
              </div>
              <div className="pbar" style={{ marginTop: 4 }}>
                <span style={{ width: `${Math.min(100, ((att[k] || 0) / maxAtt) * 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
        {att.strict && <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>strict membrane</div>}
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="spread">
          <div className="screen-title" style={{ marginBottom: 10 }}>Recent moves</div>
          <button className="action" onClick={onTick} disabled={ticking}>
            {ticking ? "reading…" : "Tick — read more"}
          </button>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={pulse}
            className="notebook"
            initial={{ opacity: 0.4 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.35 }}
          >
            {lines.length === 0 && <div className="muted">nothing logged yet</div>}
            {lines.map((l, i) => {
              const { ts, rest, warn } = parseLine(l);
              return (
                <div className={`line${warn ? " warn" : ""}`} key={i}>
                  {ts && <span className="ts">{ts}</span>} {rest}
                </div>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
