# Move the web playground under `src/` and gate it from the main CI workflow

Until now `web/` lived at the repo root and `src/` meant exactly one thing — the Python
src-layout package root (`src/spl`) for the `spl` wheel. The web playground had no CI gate:
`pages.yml` built and deployed it on every push to `main`, but nothing caught regressions on
a PR. We flip both: `web/` becomes `src/web/` (so `src/` now means *all first-party
source*, not "the Python package"), and the existing `ci.yml` grows two parallel jobs that
gate the web on every PR.

## Considered Options

- **Keep `web/` at root, no web gate** — status quo. Honest about `src/` being the Python
  package root, but lets web regressions through to Pages.
- **Keep `web/` at root, add a web CI gate** — fixes the gate without the layout shift.
  Rejected: we want the visible parity of "all first-party source under `src/`", and the
  conflict between `src/` as the import root and a separate top-level `web/` becomes harder
  to justify as the project grows.
- **Move web to `src/web/`, separate `web-ci.yml`** — independent workflow. Two YAML files
  to keep in lockstep (node version, action pins). Pure overhead given the Python and web
  gates fire on the same triggers.
- **Move web to `src/web/`, two parallel jobs in `ci.yml`** — chosen. One workflow, one
  Checks panel, four jobs (`gate`, `differential`, `web-gate`, `web-e2e`). `web-gate` gives
  fast lint/typecheck/unit feedback; `web-e2e` runs Playwright in parallel.

## Consequences

- `src/` is now polyglot: `src/spl/` is the Python package, `src/web/` is the
  Vite+React+Pyodide playground. `uv_build`'s default behavior already scopes the wheel +
  sdist to `src/<project name>` (verified: `uv build` produces a wheel containing exactly
  `spl/...` and an sdist containing exactly `src/spl/...` + pyproject + README; no `src/web`
  bleed). No `source-exclude` is required. `[tool.pyright].include` is tightened from `src`
  to `src/spl` (pyright's `include` IS its scan surface). `[tool.ruff].src` stays as
  `["src", "tests"]` — that key is ruff's import-resolution root (isort first-party
  classification), not the lint surface, and narrowing it reshuffles import ordering. The
  lint surface is narrowed by the CLI arguments instead: `ci.yml`'s `ruff check` / `ruff
  format` calls are pinned to `src/spl tests`.
- `src/web/scripts/prepare-assets.mjs` now resolves the repo root **two** levels up
  (`resolve(webRoot, "..", "..")`), so `uv build --wheel`, the spl wheel under
  `repoRoot/dist`, and the `tests/programs/` mirror source all still anchor at the repo
  root.
- `pages.yml`'s `working-directory`, `cache-dependency-path`, and Pages artifact `path`
  all gain a `src/` prefix; `pages.yml` is otherwise unchanged. ADR-0008's "self-host the
  Pyodide dist and wheels into `web/public`" decision still stands; the path is now
  `src/web/public`. Behavior unchanged.
- `ci.yml` grows two web jobs running on the same triggers as `gate` and `differential`
  (PR + push-to-main). `pages.yml` stays independent — `main` is only reachable via merged
  PRs, which `ci.yml` gates, so Pages is transitively protected without cross-workflow
  coupling. (`pages.yml` re-downloads ~6-10 MB of Pyodide assets on every push to `main`,
  and `web-e2e` does the same on every PR; we accept that. If wall-clock becomes painful
  the next step is caching `src/web/public/pyodide` + `src/web/public/wheels` keyed on
  `prepare-assets.mjs`'s pinned versions.)
- The web is now testable beyond Playwright: ESLint + Prettier for style, Vitest for fast
  unit tests. To unit-test `SplRunner` without a real browser worker, its constructor takes
  an optional `workerFactory`; the default keeps the literal
  `new Worker(new URL("./worker.ts", import.meta.url), { type: "module" })` so Vite's
  worker plugin still pattern-matches it. Coverage is report-only via Codecov flag `web`,
  mirroring the Python side's report-only stance ([`ci.yml`'s `gate` job]).
