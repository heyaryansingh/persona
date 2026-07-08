import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Python API (uvicorn persona.api.app:app --port 8000) is proxied under /api.
export default defineConfig({
  plugins: [react()],
  server: {
    // honor the PORT env the preview harness assigns (Vite ignores PORT by default)
    port: process.env.PORT ? Number(process.env.PORT) : 5173,
    strictPort: false,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
