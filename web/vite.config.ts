import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// COOP/COEP headers are required so that `crossOriginIsolated === true`, which in turn
// is required for SharedArrayBuffer + Atomics (the synchronous-input plumbing). We set
// them on BOTH the dev server and the preview server so verification works against either.
const crossOriginIsolationHeaders = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
};

export default defineConfig({
  plugins: [react()],
  // Served at the root in dev/preview/e2e; the GitHub Pages workflow sets VITE_BASE to the
  // project subpath ("/Shakespeare/"). worker.ts + examples.ts resolve assets via
  // import.meta.env.BASE_URL, so a subpath deploy works without further changes.
  base: process.env.VITE_BASE ?? "/",
  // Pyodide ships a large ESM with guarded `node:` paths; let Vite serve it as-is in dev
  // rather than esbuild-prebundling it (which trips on the node built-ins).
  optimizeDeps: { exclude: ["pyodide"] },
  server: {
    headers: crossOriginIsolationHeaders,
  },
  preview: {
    headers: crossOriginIsolationHeaders,
  },
  worker: {
    format: "es",
  },
});
