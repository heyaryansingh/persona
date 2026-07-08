import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api.js";

// ponytail: tiny line-based markdown renderer, not a full parser — enough for
// mini_review's headings/bold/lists. Swap for a markdown lib if content grows richer.
function renderMarkdown(md) {
  const lines = md.split("\n");
  const out = [];
  let listBuf = [];
  const flushList = (key) => {
    if (listBuf.length) {
      out.push(
        <ul key={`ul-${key}`} style={{ margin: "6px 0 12px", paddingLeft: 20 }}>
          {listBuf}
        </ul>
      );
      listBuf = [];
    }
  };
  const withBold = (text) => {
    const parts = text.split(/\*\*(.+?)\*\*/g);
    return parts.map((p, i) => (i % 2 === 1 ? <strong key={i}>{p}</strong> : p));
  };
  lines.forEach((raw, i) => {
    const line = raw.trimEnd();
    if (line.startsWith("# ")) {
      flushList(i);
      out.push(<h2 key={i} style={{ fontFamily: "var(--serif)", margin: "18px 0 8px" }}>{withBold(line.slice(2))}</h2>);
    } else if (line.startsWith("## ")) {
      flushList(i);
      out.push(<h3 key={i} style={{ fontFamily: "var(--serif)", margin: "14px 0 6px", fontSize: 17 }}>{withBold(line.slice(3))}</h3>);
    } else if (line.startsWith("- ")) {
      listBuf.push(<li key={i} style={{ marginBottom: 4 }}>{withBold(line.slice(2))}</li>);
    } else if (line.trim() === "") {
      flushList(i);
    } else {
      flushList(i);
      out.push(<p key={i} style={{ margin: "0 0 10px" }}>{withBold(line)}</p>);
    }
  });
  flushList("end");
  return out;
}

export default function Artifacts() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    api
      .artifacts()
      .then((d) => live && setData(d))
      .catch((e) => live && setError(e.message || "failed to load"));
    return () => {
      live = false;
    };
  }, []);

  return (
    <div>
      <div className="screen-title">Artifacts</div>
      <div className="screen-lede serif">Its body of work — can I trust it?</div>

      {error && (
        <div className="card" style={{ borderColor: "var(--human)", color: "var(--human)" }}>
          Could not load artifacts: {error}
        </div>
      )}

      {!error && !data && <div className="card muted">Loading artifacts…</div>}

      {data && (
        <div className="grid" style={{ gap: 18 }}>
          <motion.div
            className="card serif"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            {data.mini_review ? (
              renderMarkdown(data.mini_review)
            ) : (
              <div className="muted mono">No mini-review generated yet.</div>
            )}
          </motion.div>

          <motion.div
            className="card"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: 0.05 }}
            style={{ borderColor: "var(--human)" }}
          >
            <div className="screen-title" style={{ color: "var(--human)" }}>
              Times I was wrong
            </div>
            {data.error_log && data.error_log.length > 0 ? (
              <div className="notebook">
                {data.error_log.map((line, i) => (
                  <div className="line warn" key={i}>
                    {line}
                  </div>
                ))}
              </div>
            ) : (
              <div className="muted mono">No reversals recorded yet.</div>
            )}
          </motion.div>
        </div>
      )}
    </div>
  );
}
