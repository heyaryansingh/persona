// Tiny API client for the Persona backend (proxied under /api by Vite).
const j = async (r) => {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
};

export const api = {
  dashboard: () => fetch("/api/dashboard").then(j),
  notebook: (n = 60) => fetch(`/api/notebook?n=${n}`).then(j),
  beliefs: () => fetch("/api/beliefs").then(j),
  argument: (id) => fetch(`/api/argument/${encodeURIComponent(id)}`).then(j),
  dependency: () => fetch("/api/dependency").then(j),
  experiments: () => fetch("/api/experiments").then(j),
  handoffs: () => fetch("/api/handoffs").then(j),
  artifacts: () => fetch("/api/artifacts").then(j),
  tick: () => fetch("/api/tick", { method: "POST" }).then(j),
  selftest: (key) => fetch(`/api/selftest/${encodeURIComponent(key)}`, { method: "POST" }).then(j),
  resolve: (claim_key, explanation, truth) =>
    fetch("/api/resolve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim_key, explanation, truth }),
    }).then(j),
};

// Subscribe to the live notebook stream (SSE). Returns an unsubscribe fn.
export function streamNotebook(onLine) {
  const es = new EventSource("/api/stream/notebook");
  es.onmessage = (e) => {
    try { onLine(JSON.parse(e.data)); } catch {}
  };
  return () => es.close();
}
