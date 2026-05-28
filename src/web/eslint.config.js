// Flat-config ESLint for src/web. Mirrors the canonical Vite + React + TS setup, plus
// the React hooks rules (the load-bearing correctness lint for App.tsx's useEffect /
// useCallback) and react-refresh (HMR boundary check). eslint-config-prettier comes last
// to disable formatting-rule conflicts; Prettier owns formatting.

import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import prettierConfig from "eslint-config-prettier";
import globals from "globals";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "node_modules",
      "public",
      "coverage",
      "test-results",
      "playwright-report",
      "e2e/artifacts",
      "*.tsbuildinfo",
    ],
  },
  {
    files: ["**/*.{ts,tsx,js,mjs}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      // Worker globals live in `globals.worker`; the runtime mix of main-thread, worker,
      // and Node (the prepare-assets script) is small enough that one merged set is fine
      // — TS catches the real misuses, ESLint just needs no-undef happy.
      globals: { ...globals.browser, ...globals.node, ...globals.worker },
    },
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    // Register the React plugins as flat-config objects. eslint-plugin-react-hooks v7 still
    // ships its `recommended-latest` preset with the legacy `plugins: ["..."]` shape, so we
    // wire the load-bearing two rules ourselves and skip the noisier v7 extras
    // (static-components / preserve-manual-memoization / etc.) for this small codebase.
    plugins: { "react-hooks": reactHooks, "react-refresh": reactRefresh },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },
  prettierConfig,
);
