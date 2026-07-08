import { useEffect, useRef, useState, useCallback } from "react";

// Dependency-free 2D-canvas graph renderer (v3 T4). Plots server-provided node positions
// (idea_graph adds x,y in [-1,1] via a cheap O(1) layout), so it renders 10k+ nodes at
// interactive rates where Cytoscape's SVG + cose layout freezes. Pan (drag), zoom (wheel),
// click-to-select (hit test). No external graph lib.

const cssVar = (n, fb) => {
  try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || fb; }
  catch { return fb; }
};

const provColor = (p) => ({
  READ: cssVar("--ink-soft", "#8a8172"),
  INFERRED: cssVar("--ink-soft", "#8a8172"),
  HUMAN_CONFIRMED: cssVar("--anchor", "#a9a7ff"),
  TESTED: cssVar("--live", "#4fd0a0"),
}[p] || cssVar("--ink-soft", "#8a8172"));

export default function GraphCanvas({ nodes, edges, cutoff, onSelect, height = 560 }) {
  const canvasRef = useRef(null);
  const view = useRef({ scale: 1, tx: 0, ty: 0 });
  const drag = useRef(null);
  const [selId, setSelId] = useState(null);

  const project = useCallback((n, w, h) => {
    const R = Math.min(w, h) * 0.46;
    const v = view.current;
    return [w / 2 + n.x * R * v.scale + v.tx, h / 2 + n.y * R * v.scale + v.ty];
  }, []);

  const draw = useCallback(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth, h = cv.clientHeight;
    if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const pos = new Map();
    for (const n of nodes) pos.set(n.id, project(n, w, h));
    const dimmed = (n) => cutoff && n.first_seen && n.first_seen > cutoff;
    const dimSet = new Set(nodes.filter(dimmed).map((n) => n.id));

    // edges
    ctx.lineWidth = 0.6;
    for (const e of edges) {
      const a = pos.get(e.source), b = pos.get(e.target);
      if (!a || !b) continue;
      const faded = dimSet.has(e.source) || dimSet.has(e.target);
      ctx.strokeStyle = cssVar("--rule", "#3a362c");
      ctx.globalAlpha = faded ? 0.05 : (e.kind === "shares" ? 0.28 : 0.5);
      ctx.beginPath();
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
      if (e.kind && e.kind !== "shares") ctx.setLineDash([4, 3]); else ctx.setLineDash([]);
      ctx.stroke();
    }
    ctx.setLineDash([]); ctx.globalAlpha = 1;

    // nodes (label only the most load-bearing to avoid clutter)
    const labelled = [...nodes].sort((a, b) => (b.load_bearing || 0) - (a.load_bearing || 0)).slice(0, 40);
    const labelIds = new Set(labelled.map((n) => n.id));
    for (const n of nodes) {
      const [x, y] = pos.get(n.id);
      const rad = Math.max(2.5, Math.min(22, 3 + (n.load_bearing || 0) * 220)) * Math.sqrt(view.current.scale);
      ctx.globalAlpha = dimSet.has(n.id) ? 0.12 : 1;
      ctx.beginPath();
      ctx.arc(x, y, rad, 0, 2 * Math.PI);
      ctx.fillStyle = provColor(n.provenance_state);
      ctx.fill();
      if (n.anchor) { ctx.lineWidth = 2; ctx.strokeStyle = cssVar("--anchor", "#a9a7ff"); ctx.stroke(); }
      if (n.id === selId) { ctx.lineWidth = 2.5; ctx.strokeStyle = cssVar("--live", "#4fd0a0"); ctx.stroke(); }
      if (labelIds.has(n.id) && view.current.scale > 0.6) {
        ctx.globalAlpha = dimSet.has(n.id) ? 0.2 : 0.8;
        ctx.fillStyle = cssVar("--ink-soft", "#8a8172");
        ctx.font = "9px monospace";
        ctx.fillText((n.entities || []).slice(0, 2).join(" · ") || n.statement.slice(0, 20), x + rad + 2, y + 3);
      }
    }
    ctx.globalAlpha = 1;
  }, [nodes, edges, cutoff, selId, project]);

  useEffect(() => { const id = requestAnimationFrame(draw); return () => cancelAnimationFrame(id); }, [draw]);

  // redraw when the container gets/changes width (e.g. 0 -> N on first layout, sidebar toggle,
  // window resize) — without this the canvas can mount at 0 width and never paint.
  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => requestAnimationFrame(draw));
    ro.observe(cv);
    return () => ro.disconnect();
  }, [draw]);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv) return;
    const onWheel = (ev) => {
      ev.preventDefault();
      const v = view.current;
      const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
      v.scale = Math.max(0.2, Math.min(8, v.scale * factor));
      draw();
    };
    const onDown = (ev) => { drag.current = { x: ev.clientX, y: ev.clientY, tx: view.current.tx, ty: view.current.ty, moved: false }; };
    const onMove = (ev) => {
      if (!drag.current) return;
      const dx = ev.clientX - drag.current.x, dy = ev.clientY - drag.current.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) drag.current.moved = true;
      view.current.tx = drag.current.tx + dx; view.current.ty = drag.current.ty + dy;
      draw();
    };
    const onUp = (ev) => {
      const wasDrag = drag.current && drag.current.moved;
      drag.current = null;
      if (wasDrag) return;
      // click hit-test
      const rect = cv.getBoundingClientRect();
      const mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
      const w = cv.clientWidth, h = cv.clientHeight;
      let best = null, bestD = 16 * 16;
      for (const n of nodes) {
        const [x, y] = project(n, w, h);
        const d = (x - mx) ** 2 + (y - my) ** 2;
        if (d < bestD) { bestD = d; best = n; }
      }
      setSelId(best ? best.id : null);
      onSelect && onSelect(best || null);
    };
    cv.addEventListener("wheel", onWheel, { passive: false });
    cv.addEventListener("mousedown", onDown);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      cv.removeEventListener("wheel", onWheel);
      cv.removeEventListener("mousedown", onDown);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [nodes, draw, project, onSelect]);

  return <canvas ref={canvasRef} style={{ width: "100%", height, display: "block", cursor: "grab" }} />;
}
