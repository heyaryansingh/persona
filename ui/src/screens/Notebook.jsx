import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, streamNotebook } from "../api.js";

// parses "- `<ts>` <text>" -> {ts, text}. Falls back to raw line if it doesn't match.
function parseLine(raw) {
  const m = /^- `([^`]*)`\s?(.*)$/.exec(raw);
  if (m) return { ts: m[1], text: m[2] };
  return { ts: "", text: raw };
}

export default function Notebook() {
  const [lines, setLines] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const seen = useRef(new Set());
  const bottomRef = useRef(null);

  useEffect(() => {
    let unsub = () => {};
    let cancelled = false;

    (async () => {
      try {
        const { lines: initial } = await api.notebook(150);
        if (cancelled) return;
        const list = initial || [];
        list.forEach((l) => seen.current.add(l));
        setLines(list);
        setStatus("ready");
      } catch {
        if (!cancelled) setStatus("error");
      }

      unsub = streamNotebook((line) => {
        if (typeof line !== "string" || seen.current.has(line)) return;
        seen.current.add(line);
        setLines((prev) => [...prev, line]);
      });
    })();

    return () => {
      cancelled = true;
      unsub();
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [lines]);

  return (
    <div className="card">
      <div className="screen-title">Notebook</div>
      <div className="screen-lede">
        The researcher's real move-by-move stream — every notice, every spawned reader, every belief update, as it happens.
      </div>

      {status === "loading" && <div className="muted">loading notebook…</div>}
      {status === "error" && <div className="muted">couldn't reach the notebook stream — is the backend running?</div>}
      {status === "ready" && lines.length === 0 && (
        <div className="muted">nothing logged yet — the researcher hasn't made a move.</div>
      )}

      {status === "ready" && lines.length > 0 && (
        <div className="notebook" style={{ maxHeight: 560, overflowY: "auto" }}>
          <AnimatePresence initial={false}>
            {lines.map((raw, i) => {
              const { ts, text } = parseLine(raw);
              const warn = text.includes("⚠");
              return (
                <motion.div
                  key={raw + i}
                  className={`line${warn ? " warn" : ""}`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25 }}
                >
                  {ts && <span className="ts">{ts}</span>} {text}
                </motion.div>
              );
            })}
          </AnimatePresence>
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
