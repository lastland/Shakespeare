# shakespeare

`src/` is polyglot post-[ADR-0010](docs/adr/0010-polyglot-src-layout-and-web-ci-gating.md):
`src/spl/` is the Python package, `src/web/` is the Vite+React+Pyodide playground. Don't assume
`src/` ⇒ Python.

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context (`CONTEXT.md` + `docs/adr/` at the repo root). See `docs/agents/domain.md`.

### Web playground

`src/web/` runs the `spl` wheel in-browser via Pyodide (see ADRs 0008, 0009, 0010). Local
commands from `src/web/`: `npm run lint`, `npm run format:check`, `npm run typecheck`,
`npm run test:coverage`, `npm run e2e`. README has the full development section.
