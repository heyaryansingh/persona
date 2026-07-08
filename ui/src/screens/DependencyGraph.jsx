import { useEffect, useRef, useState } from "react";
import cytoscape from "cytoscape";
import { api } from "../api.js";

const truncate = (s, n = 46) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s || "");

export default function DependencyGraph() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const cyRef = useRef(null);
  const cyInstance = useRef(null);

  useEffect(() => {
    let alive = true;
    api
      .dependency()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(String(e)));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!data || !cyRef.current || data.nodes.length === 0) return;

    const nodesById = new Map(data.nodes.map((n) => [n.claim_id, n]));
    const elements = [
      ...data.nodes.map((n) => ({
        data: {
          id: n.claim_id,
          label: truncate(n.statement),
          load_bearing: n.load_bearing || 0,
        },
      })),
      ...data.edges.map((e, i) => ({
        data: {
          id: `e${i}`,
          source: e.src,
          target: e.dst,
          confidence: e.confidence,
          candidate: e.candidate,
        },
      })),
    ];

    const cy = cytoscape({
      container: cyRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-family": "IBM Plex Mono, monospace",
            "font-size": 9,
            color: "#23201b",
            "text-wrap": "wrap",
            "text-max-width": "90px",
            "background-color": "#fbfaf6",
            "border-color": "#6b6459",
            "border-width": 1.5,
            width: "mapData(load_bearing, 0, 1, 26, 64)",
            height: "mapData(load_bearing, 0, 1, 26, 64)",
            "text-valign": "bottom",
            "text-margin-y": 6,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#b4471f",
            "target-arrow-color": "#b4471f",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "line-style": "dashed",
            opacity: 0.8,
          },
        },
        {
          selector: "node:selected",
          style: { "border-color": "#1f7a5a", "border-width": 3 },
        },
      ],
      layout: { name: "cose", animate: false, padding: 24 },
    });

    cy.on("tap", "node", (evt) => {
      const id = evt.target.id();
      setSelected(nodesById.get(id) || null);
    });
    cy.on("tap", (evt) => {
      if (evt.target === cy) setSelected(null);
    });

    cyInstance.current = cy;
    return () => {
      cy.destroy();
      cyInstance.current = null;
    };
  }, [data]);

  if (error) {
    return (
      <div>
        <div className="screen-title">Dependency Graph</div>
        <p className="screen-lede">What is this field standing on?</p>
        <div className="card">
          <p className="muted">Could not load the dependency graph: {error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <div className="screen-title">Dependency Graph</div>
        <p className="screen-lede">What is this field standing on?</p>
        <div className="card">
          <p className="muted">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="screen-title">Dependency Graph</div>
      <p className="screen-lede">What is this field standing on?</p>

      {data.note && (
        <div className="card" style={{ marginBottom: 14 }}>
          <p className="mono muted" style={{ margin: 0, fontSize: 12 }}>
            {data.note}
          </p>
        </div>
      )}

      {data.nodes.length === 0 ? (
        <div className="card">
          <p className="serif" style={{ marginTop: 0 }}>
            No inferential-dependency edges yet.
          </p>
          <p className="muted">
            These <span className="mono">derives-from</span> edges are extracted as{" "}
            <span className="chip">CANDIDATE</span> and gated by experiment E6; the offline
            heuristic extractor emits <span className="mono">support</span>/
            <span className="mono">contradict</span>, not <span className="mono">derives-from</span>.
          </p>
        </div>
      ) : (
        <div className="grid cols-2" style={{ gridTemplateColumns: "1fr 320px" }}>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div ref={cyRef} style={{ width: "100%", height: 520 }} />
          </div>
          <div className="card">
            {selected ? (
              <>
                <div className="row" style={{ marginBottom: 8 }}>
                  <span className="chip">
                    load-bearing {Math.round((selected.load_bearing || 0) * 100)}%
                  </span>
                </div>
                <p className="serif" style={{ marginTop: 0 }}>{selected.statement}</p>
                <p className="muted" style={{ fontSize: 12.5 }}>
                  If this claim fell, everything downstream that derives from it weakens —
                  candidate edges are dashed because they are inferred, not confirmed.
                </p>
              </>
            ) : (
              <p className="muted">Click a node to inspect the claim it rests on.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
