import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";

const cssVar = (n, fb) => {
  try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || fb; }
  catch { return fb; }
};

const PROV_COLOR = () => ({
  READ: cssVar("--ink-soft", "#8a8172"),
  INFERRED: cssVar("--ink-soft", "#8a8172"),
  HUMAN_CONFIRMED: cssVar("--anchor", "#a9a7ff"),
  TESTED: cssVar("--live", "#4fd0a0"),
});

export default function IdeaGraph() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [sel, setSel] = useState(null);
  const [tIdx, setTIdx] = useState(null); // index into sorted timestamps; null = all
  const box = useRef(null);
  const cyRef = useRef(null);

  useEffect(() => {
    fetch("/api/idea-graph").then((r) => r.json()).then(setData).catch((e) => setErr(String(e)));
  }, []);

  // sorted unique timestamps for the scrubber
  const stamps = data ? Array.from(new Set((data.timeline || []).map((e) => e.ts).filter(Boolean))).sort() : [];
  const cutoff = tIdx == null ? null : stamps[Math.min(tIdx, stamps.length - 1)];

  useEffect(() => {
    if (!data || !box.current) return;
    const prov = PROV_COLOR();
    const nodes = (data.nodes || []).map((n) => ({ data: { ...n, label: (n.entities || []).slice(0, 2).join(" · ") || n.statement.slice(0, 22) } }));
    const edges = (data.edges || []).map((e, i) => ({ data: { id: `e${i}`, source: e.source, target: e.target, kind: e.kind, w: e.weight || 1 } }))
      .filter((e) => nodes.find((n) => n.data.id === e.data.source) && nodes.find((n) => n.data.id === e.data.target));
    const cy = cytoscape({
      container: box.current,
      elements: { nodes, edges },
      style: [
        { selector: "node", style: {
            "background-color": (el) => prov[el.data("provenance_state")] || prov.READ,
            width: (el) => Math.max(12, Math.min(60, 12 + (el.data("load_bearing") || 0) * 260)),
            height: (el) => Math.max(12, Math.min(60, 12 + (el.data("load_bearing") || 0) * 260)),
            "border-width": (el) => (el.data("anchor") ? 3 : 0.5),
            "border-color": cssVar("--anchor", "#a9a7ff"),
            label: "data(label)", "font-size": 6, color: cssVar("--ink-soft", "#8a8172"),
            "font-family": "monospace", "text-wrap": "ellipsis", "text-max-width": 60,
            "min-zoomed-font-size": 7 } },
        { selector: "edge", style: {
            width: (el) => Math.min(3, 0.4 + el.data("w") * 0.4),
            "line-color": cssVar("--rule", "#3a362c"), "curve-style": "haystack", opacity: 0.5,
            "line-style": (el) => (el.data("kind") === "derives-from" ? "dashed" : "solid") } },
        { selector: "node.dim", style: { opacity: 0.12 } },
        { selector: "node:selected", style: { "border-width": 3, "border-color": cssVar("--live", "#4fd0a0") } },
      ],
      layout: { name: "cose", animate: false, nodeRepulsion: 6000, idealEdgeLength: 40 },
    });
    cy.on("tap", "node", (evt) => setSel(evt.target.data()));
    cy.on("tap", (evt) => { if (evt.target === cy) setSel(null); });
    cyRef.current = cy;
    return () => cy.destroy();
  }, [data]);

  // time scrubber: dim nodes born after the cutoff
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.nodes().forEach((n) => {
        const fs = n.data("first_seen");
        n.toggleClass("dim", !!(cutoff && fs && fs > cutoff));
      });
    });
  }, [cutoff, data]);

  if (err) return (<div><div className="screen-title">Idea Graph</div><p className="muted mono">Could not load: {err}</p></div>);
  if (!data) return (<div><div className="screen-title">Idea Graph</div><p className="muted mono">building the graph…</p></div>);

  const empty = (data.nodes || []).length === 0;

  return (
    <div>
      <div className="screen-title">Idea Graph</div>
      <div className="screen-lede">What does this field rest on — and how did it get here?</div>

      {empty ? (
        <div className="card muted mono">No beliefs yet — run the swarm to populate the idea graph.</div>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: sel ? "1fr 300px" : "1fr", gap: 14 }}>
          <div className="card" style={{ padding: 0, position: "relative" }}>
            <div ref={box} style={{ width: "100%", height: 560 }} />
            <div className="row mono" style={{ position: "absolute", left: 12, bottom: 10, gap: 12, fontSize: 10.5, flexWrap: "wrap" }}>
              <span className="muted">provenance:</span>
              <span style={{ color: cssVar("--ink-soft") }}>● READ</span>
              <span style={{ color: cssVar("--anchor") }}>● HUMAN_CONFIRMED</span>
              <span style={{ color: cssVar("--live") }}>● TESTED</span>
              <span className="muted">— size = load-bearing · dashed = derives-from (candidate)</span>
            </div>
          </div>

          {sel && (
            <div className="card">
              <div className="screen-title" style={{ marginBottom: 8 }}>Claim</div>
              <p className="serif" style={{ margin: "0 0 10px" }}>{sel.statement}</p>
              <div className="row" style={{ gap: 6, marginBottom: 8, flexWrap: "wrap" }}>
                <span className={`prov ${sel.provenance_state}`}>{sel.provenance_state}</span>
                <span className="chip">{sel.state}</span>
                <span className="chip">{sel.independent_sources} src</span>
              </div>
              <div className="muted mono" style={{ fontSize: 11, marginBottom: 4 }}>calibrated p = {sel.calibrated_p}</div>
              <div className="pbar" style={{ marginBottom: 10 }}><span style={{ width: `${(sel.calibrated_p || 0) * 100}%` }} /></div>
              <div className="muted mono" style={{ fontSize: 11 }}>entities: {(sel.entities || []).join(", ")}</div>
              <div className="muted mono" style={{ fontSize: 10.5, marginTop: 8 }}>
                first seen {String(sel.first_seen).slice(0, 19)}<br />updated {String(sel.last_update).slice(0, 19)} · {sel.n_updates} updates
              </div>
            </div>
          )}
        </div>
      )}

      {!empty && stamps.length > 1 && (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="spread">
            <div className="screen-title">Time scrubber</div>
            <span className="muted mono" style={{ fontSize: 11 }}>{cutoff ? String(cutoff).slice(0, 19) : "all time"}</span>
          </div>
          <input type="range" min={0} max={stamps.length - 1} value={tIdx == null ? stamps.length - 1 : tIdx}
                 onChange={(e) => setTIdx(Number(e.target.value))} style={{ width: "100%" }} />
          <div className="muted mono" style={{ fontSize: 10.5 }}>drag to replay how the field's ideas emerged; nodes born later fade out</div>
        </div>
      )}
      <div className="muted mono" style={{ fontSize: 10.5, marginTop: 10 }}>{data.note}</div>
    </div>
  );
}
