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
  // Relative base so the build can be deployed under a GitHub Pages subpath later.
  base: "./",
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
