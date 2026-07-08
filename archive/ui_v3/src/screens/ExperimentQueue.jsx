import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api.js";

// cost tiers: 1 = existing-data, 3 = cheap-assay, 10 = expensive-study
// ponytail: fixed thresholds match the three cost buckets the backend actually emits (1/3/10);
// add a real lookup table if the backend starts returning arbitrary cost values.
function costTier(cost) {
  if (cost <= 1) return "existing-data";
  if (cost <= 3) return "cheap-assay";
  return "expensive-study";
}

export default function ExperimentQueue() {
  const [queue, setQueue] = useState(null);
  const [statements, setStatements] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [exp, bel] = await Promise.all([api.experiments(), api.beliefs()]);
        if (cancelled) return;
        const map = {};
        for (const b of bel.beliefs || []) map[b.claim_id] = b.statement;
        setStatements(map);
        setQueue(exp.queue || []);
      } catch (e) {
        if (!cancelled) setError(e.message || "failed to load");
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div>
      <div className="screen-title">Experiment Queue</div>
      <div className="screen-lede">The single highest-leverage experiment</div>

      {error && <div className="card muted">Could not load the queue: {error}</div>}

      {!error && queue === null && <div className="card muted">Loading queue…</div>}

      {!error && queue && queue.length === 0 && (
        <div className="card muted">No experiments queued right now.</div>
      )}

      {!error && queue && queue.length > 0 && (
        <div className="grid" style={{ gap: 10 }}>
          {queue.map((item, i) => (
            <motion.div
              key={item.exp_id}
              className="card"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: i * 0.03 }}
              style={i === 0 ? { borderColor: "var(--live)", boxShadow: "0 0 0 1px var(--live)" } : undefined}
            >
              <div className="spread">
                <div className="row" style={{ gap: 14 }}>
                  <span className="mono muted" style={{ fontSize: 12, minWidth: 18 }}>
                    #{i + 1}
                  </span>
                  <span className="serif" style={{ fontSize: 16 }}>
                    {statements[item.exp_id] || item.exp_id}
                  </span>
                </div>
                <span className="mono" style={{ fontWeight: 600, fontSize: 15 }}>
                  {item.score.toFixed(2)}
                </span>
              </div>
              <div className="row muted mono" style={{ fontSize: 11.5, marginTop: 8, gap: 18 }}>
                <span>VoI {item.voi.toFixed(2)}</span>
                <span>cost {item.cost} · {costTier(item.cost)}</span>
                <span>score = VoI / cost</span>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <div className="muted mono" style={{ fontSize: 11, marginTop: 18 }}>
        VoI is experimental — the baseline to beat is the Open Targets genetic-evidence prior
        (2.6x clinical success), not raw citations (gate E7).
      </div>
    </div>
  );
}
