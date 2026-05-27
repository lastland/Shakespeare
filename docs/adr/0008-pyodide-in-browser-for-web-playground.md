# Run the interpreter in-browser via Pyodide for the web playground

The web interface is a **pure-frontend playground** (additive to the CLI, which remains the primary
installed entry point). We run the *existing* Python interpreter in the browser via **Pyodide**
(CPython compiled to WebAssembly) rather than reimplementing it in TypeScript or standing up a
server. The browser loads the same `spl` wheel the CLI installs, so the entire conformance-tested
stack — parser, analyzer, interpreter, vocabulary, every ADR decision, and the differential harness —
is reused unchanged.

## Considered Options

- **Reimplement in TypeScript** — rejected. Duplicates the whole interpreter, discards every
  decision recorded in ADR-0001…0007, and abandons the differential harness; two implementations
  would inevitably diverge.
- **Thin server (FastAPI) running the Python interpreter** — rejected. Not pure-frontend; needs
  hosting and a network round-trip per run.
- **Pyodide (WASM)** — chosen. The only option that is simultaneously pure-frontend *and* reuses the
  existing code.

## Consequences

- Pyodide 0.28+ ships **CPython 3.13**, satisfying `requires-python = ">=3.13"`; `lark` is pure
  Python and installs via `micropip`. (Both verified before adopting this path — the 3.13 floor was
  the load-bearing risk.)
- A ~6–10 MB runtime download plus a few-second cold start, mitigated by self-hosting and browser
  caching. Acceptable for an esolang playground.
- Pyodide runs in a **Web Worker** so a runaway SPL loop (looping is idiomatic in the language) can
  be hard-cancelled via `worker.terminate()` + respawn; program output **streams** to the UI via
  `postMessage`.
- The interpreter's IO seam — `Interpreter(program, io=...)` — is the *only* integration point. A
  custom `IO` (Python, constructed in the worker) bridges browser I/O. **No interpreter changes** in
  phase 1.
- We **self-host** the Pyodide dist and the `spl` + pinned `lark` wheels (build step: `uv build` →
  copy into `web/public`). This keeps the playground reproducible, version-pinned, offline-capable,
  and free of cross-origin asset friction under the cross-origin isolation that
  [ADR-0009](0009-interactive-stdin-via-sharedarraybuffer.md) requires.
- A live runtime **visualizer/debugger** (showing the Stage, each Character's Value and Stack, the
  program counter, and giving `[A pause]` real meaning) is deferred to a phase 2 that adds a
  behavior-preserving stepping API to the backend; phase 1 touches no backend code.
