import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api.js";

// ponytail: dot count is a capped visual sample of attention counts, not a 1:1 render of every doc/candidate.
function Dots({ n, color, keyPrefix }) {
  const count = Math.max(0, Math.min(12, n || 0));
  return (
    <div className="row" style={{ flexWrap: "wrap", minHeight: 22 }}>
      {Array.from({ length: count }).map((_, i) => (
        <motion.span
          key={`${keyPrefix}-${i}`}
          initial={{ opacity: 0, x: -14 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.03 }}
          style={{
            display: "inline-block",
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: color,
            margin: 2,
          }}
        />
      ))}
    </div>
  );
}

export default function SwarmView() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [ticking, setTicking] = useState(false);
  const [gen, setGen] = useState(0); // bump to retrigger flow animation

  const load = useCallback(async () => {
    try {
      const d = await api.dashboard();
      setData(d);
      setError(null);
    } catch (e) {
      setError(e.message || "failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onTick = async () => {
    setTicking(true);
    try {
      await api.tick();
      await load();
      setGen((g) => g + 1);
    } catch (e) {
      setError(e.message || "tick failed");
    } finally {
      setTicking(false);
    }
  };

  if (loading) {
    return (
      <div>
        <div className="screen-title">Swarm</div>
        <div className="screen-lede">Scale of reading, discipline of believing.</div>
        <div className="muted mono">loading…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="screen-title">Swarm</div>
        <div className="screen-lede">Scale of reading, discipline of believing.</div>
        <div className="card" style={{ borderColor: "var(--human)" }}>
          <span className="muted">could not reach the backend: {error}</span>
        </div>
      </div>
    );
  }

  const att = data?.attention || {};
  const nBeliefs = data?.n_beliefs ?? 0;

  return (
    <div>
      <div className="spread" style={{ marginBottom: 4 }}>
        <div>
          <div className="screen-title">Swarm</div>
          <div className="screen-lede">Scale of reading, discipline of believing.</div>
        </div>
        <button className="action" onClick={onTick} disabled={ticking}>
          {ticking ? "ticking…" : "Tick"}
        </button>
      </div>

      <div className="grid cols-3">
        {/* Stage 1: Swarm */}
        <div className="card">
          <div className="spread">
            <span className="mono" style={{ fontWeight: 600 }}>1. SWARM</span>
            <span className="chip live">reading</span>
          </div>
          <div className="muted" style={{ marginTop: 8, marginBottom: 6 }}>
            {att.docs_read ?? 0} docs read → {att.candidates ?? 0} candidates
          </div>
          <AnimatePresence mode="wait">
            <Dots key={`swarm-${gen}`} n={att.candidates} color="var(--ink-soft)" keyPrefix={`s${gen}`} />
          </AnimatePresence>
        </div>

        {/* Stage 2: Membrane */}
        <div className="card">
          <div className="spread">
            <span className="mono" style={{ fontWeight: 600 }}>2. MEMBRANE</span>
            <span className="chip human">the anti-slop funnel</span>
          </div>
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
            <div className="row spread">
              <span className="muted">committed</span>
              <span className="chip live">{att.committed ?? 0}</span>
            </div>
            <div className="row spread">
              <span className="muted">held</span>
              <span className="chip">{att.held ?? 0}</span>
            </div>
            <div className="row spread">
              <span className="muted">contradictions</span>
              <span className="chip human">{att.contradictions ?? 0}</span>
            </div>
            {!!att.strict && (
              <div className="row spread">
                <span className="muted">strict-mode claims</span>
                <span className="chip human">{att.strict}</span>
              </div>
            )}
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={`mem-${gen}`} style={{ marginTop: 8 }}>
              <Dots n={att.committed} color="var(--live)" keyPrefix={`c${gen}`} />
              <Dots n={att.held} color="var(--human)" keyPrefix={`h${gen}`} />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Stage 3: Self */}
        <div className="card">
          <div className="spread">
            <span className="mono" style={{ fontWeight: 600 }}>3. SELF</span>
            <span className="chip">{data?.name || "persona"}</span>
          </div>
          <div className="muted" style={{ marginTop: 8, marginBottom: 6 }}>
            durable beliefs held
          </div>
          <motion.div
            key={`nb-${gen}-${nBeliefs}`}
            initial={{ scale: 0.9, opacity: 0.4 }}
            animate={{ scale: 1, opacity: 1 }}
            className="serif"
            style={{ fontSize: 34 }}
          >
            {nBeliefs}
          </motion.div>
        </div>
      </div>

      <div className="muted" style={{ marginTop: 14, fontSize: 12 }}>
        Committed candidates cross into the self; held candidates bounce back for more evidence.
        The membrane is the anti-slop funnel — scale of reading, discipline of believing.
      </div>
    </div>
  );
}
