import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const MAX_DOTS = 200;

// ponytail: dot color by agent state — reading (soft), done (live), error (human).
function dotColor(agent) {
  if (agent.state === "reading") return "var(--ink-soft)";
  if (agent.ok === false) return "var(--human)";
  return "var(--live)";
}

export default function SwarmView() {
  const [limit, setLimit] = useState(10);
  const [running, setRunning] = useState(false);
  const [agents, setAgents] = useState([]); // [{doc_id, group, title, state, ok}]
  const [nSpawned, setNSpawned] = useState(0);
  const [nReturned, setNReturned] = useState(0);
  const [lastGroup, setLastGroup] = useState(null);
  const [admitted, setAdmitted] = useState(0);
  const [held, setHeld] = useState(0);
  const [contradictions, setContradictions] = useState(0);
  const [claims, setClaims] = useState(0);
  const [committed, setCommitted] = useState(0);
  const [spent, setSpent] = useState(0);
  const [errors, setErrors] = useState(0);
  const [pulse, setPulse] = useState(null); // 'admit' | 'reject' | 'flag'
  const [error, setError] = useState(null);
  const agentsRef = useRef(new Map()); // doc_id -> agent (dedup across replayed backlog)

  useEffect(() => {
    const es = new EventSource("/api/stream/swarm");
    es.onmessage = (e) => {
      let ev;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return;
      }
      handleEvent(ev);
    };
    es.onerror = () => setError("stream disconnected");
    return () => es.close();
  }, []);

  function handleEvent(ev) {
    switch (ev.type) {
      case "run_start":
        setRunning(true);
        agentsRef.current = new Map();
        setAgents([]);
        setNSpawned(0);
        setNReturned(0);
        setLastGroup(null);
        setAdmitted(0);
        setHeld(0);
        setContradictions(0);
        setClaims(0);
        setCommitted(0);
        setSpent(0);
        setErrors(0);
        setError(null);
        break;
      case "spawn": {
        const m = agentsRef.current;
        if (!m.has(ev.doc_id)) {
          m.set(ev.doc_id, {
            doc_id: ev.doc_id,
            group: ev.group,
            title: ev.title,
            state: "reading",
          });
          setNSpawned((n) => n + 1);
          setAgents(Array.from(m.values()));
        }
        break;
      }
      case "read": {
        const m = agentsRef.current;
        const prev = m.get(ev.doc_id);
        if (!prev || prev.state !== "done") {
          m.set(ev.doc_id, {
            doc_id: ev.doc_id,
            group: ev.group ?? prev?.group,
            title: ev.title ?? prev?.title,
            state: "done",
            ok: ev.ok,
          });
          setNReturned((n) => n + 1);
          setClaims((n) => n + (ev.n_claims || 0));
          if (ev.ok === false) setErrors((n) => n + 1);
          setLastGroup(ev.group ?? prev?.group ?? null);
          setAgents(Array.from(m.values()));
        }
        break;
      }
      case "admit":
        setAdmitted((n) => n + 1);
        setCommitted((n) => n + 1);
        setPulse(`admit-${ev.claim_key}-${ev.t}`);
        break;
      case "reject":
        setHeld((n) => n + 1);
        setPulse(`reject-${ev.claim_key}-${ev.t}`);
        break;
      case "flag":
        setContradictions((n) => n + 1);
        setPulse(`flag-${ev.claim_key}-${ev.t}`);
        break;
      case "run_done":
        setRunning(false);
        if (typeof ev.spent_usd === "number") setSpent(ev.spent_usd);
        break;
      case "run_error":
        setRunning(false);
        setError(String(ev.error || "run failed"));
        break;
      default:
        break;
    }
  }

  const onRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await fetch(`/api/swarm/run?limit=${limit}`, { method: "POST" });
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    } catch (e) {
      setError(e.message || "failed to start run");
      setRunning(false);
    }
  };

  const shown = agents.slice(0, MAX_DOTS);
  const overflow = agents.length - shown.length;
  const idle = agents.length === 0 && !running;

  return (
    <div>
      <div className="spread" style={{ marginBottom: 4 }}>
        <div>
          <div className="screen-title">Swarm Control Room</div>
          <div className="screen-lede">Scale of reading, discipline of believing.</div>
        </div>
        <div className="row">
          <input
            type="number"
            min={4}
            max={30}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value) || 10)}
            disabled={running}
            className="mono"
            style={{
              width: 52,
              background: "var(--paper)",
              border: "1px solid var(--rule)",
              borderRadius: 6,
              color: "var(--ink)",
              padding: "5px 6px",
            }}
          />
          <button className="action" onClick={onRun} disabled={running}>
            {running ? "running…" : "Run swarm"}
          </button>
        </div>
      </div>

      {error && (
        <div className="card" style={{ borderColor: "var(--human)", marginBottom: 14 }}>
          <span className="muted">{error}</span>
        </div>
      )}

      {idle ? (
        <div className="card">
          <span className="muted mono">Idle — press Run swarm to watch it read.</span>
        </div>
      ) : (
        <div className="grid cols-3">
          {/* Stage 1: Swarm */}
          <div className="card">
            <div className="spread">
              <span className="mono" style={{ fontWeight: 600 }}>1. SWARM</span>
              {running && <span className="chip live">reading</span>}
            </div>
            <div className="muted" style={{ marginTop: 8, marginBottom: 8, fontSize: 12.5 }}>
              {nSpawned} agents spawned / {nReturned} returned
              {lastGroup ? ` — latest: ${String(lastGroup)}` : ""}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 4, minHeight: 22 }}>
              <AnimatePresence initial={false}>
                {shown.map((a) => (
                  <motion.span
                    key={a.doc_id}
                    initial={{ opacity: 0, scale: 0.4 }}
                    animate={{ opacity: 1, scale: 1 }}
                    title={`${a.title || a.doc_id}${a.group ? " — " + a.group : ""}`}
                    style={{
                      display: "inline-block",
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: dotColor(a),
                    }}
                  />
                ))}
              </AnimatePresence>
              {overflow > 0 && (
                <span className="muted mono" style={{ fontSize: 11 }}>
                  +{overflow} more
                </span>
              )}
            </div>
          </div>

          {/* Stage 2: Membrane */}
          <div className="card">
            <div className="spread">
              <span className="mono" style={{ fontWeight: 600 }}>2. MEMBRANE</span>
              <span className="chip human">the anti-slop funnel</span>
            </div>
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
              <div className="row spread">
                <span className="muted">admitted</span>
                <motion.span
                  key={`admit-${admitted}`}
                  initial={{ scale: 1.35 }}
                  animate={{ scale: 1 }}
                  className="chip live"
                >
                  {admitted}
                </motion.span>
              </div>
              <div className="row spread">
                <span className="muted">held / rejected</span>
                <motion.span
                  key={`held-${held}`}
                  initial={{ scale: 1.35 }}
                  animate={{ scale: 1 }}
                  className="chip"
                >
                  {held}
                </motion.span>
              </div>
              <div className="row spread">
                <span className="muted">contradictions flagged</span>
                <motion.span
                  key={`contra-${contradictions}`}
                  initial={{ scale: 1.35 }}
                  animate={{ scale: 1 }}
                  className="chip human"
                >
                  {contradictions}
                </motion.span>
              </div>
            </div>
          </div>

          {/* Stage 3: Self */}
          <div className="card">
            <div className="spread">
              <span className="mono" style={{ fontWeight: 600 }}>3. SELF</span>
              {running ? (
                <span className="chip live">running</span>
              ) : (
                <span className="chip">idle</span>
              )}
            </div>
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
              <div className="row spread">
                <span className="muted">claims extracted</span>
                <span className="chip">{claims}</span>
              </div>
              <div className="row spread">
                <span className="muted">beliefs committed</span>
                <span className="chip live">{committed}</span>
              </div>
              <div className="row spread">
                <span className="muted">cost</span>
                <span className="chip">${spent.toFixed(4)}</span>
              </div>
              <div className="row spread">
                <span className="muted">errors</span>
                <span className={errors > 0 ? "chip human" : "chip"}>{errors}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="muted" style={{ marginTop: 14, fontSize: 12 }}>
        the membrane admits only convergent, independent, calibrated signal — scale of reading,
        discipline of believing.
      </div>
    </div>
  );
}
