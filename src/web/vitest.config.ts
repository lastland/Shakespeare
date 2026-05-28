// Vitest config for the web unit tests. Distinct from Playwright (e2e/), which runs the
// full browser stack against `vite preview`. Unit tests live colocated as `*.test.ts` next
// to their sources and run in Node — SharedArrayBuffer, Atomics, and TextEncoder are all
// native in Node, so SplRunner's coordinator logic is testable without a browser worker
// once a fake worker is injected via its `workerFactory` ctor seam.

import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reporter: ["text-summary", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/**/*.d.ts",
        // App.tsx is React UI tied to the worker; covered by Playwright e2e, not vitest.
        "src/App.tsx",
        "src/main.tsx",
        // The worker runs Pyodide; only exercisable in the browser via e2e.
        "src/worker.ts",
      ],
    },
  },
});
