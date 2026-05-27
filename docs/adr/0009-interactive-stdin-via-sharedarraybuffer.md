# Interactive stdin via SharedArrayBuffer under cross-origin isolation

The playground offers **interactive stdin** — the user types input as the program runs, as in a
terminal. We implement it by having the worker's *synchronous* Python reads block on a
**`SharedArrayBuffer` via `Atomics.wait`** while the main thread collects input and writes it back.
This keeps the interpreter's synchronous `read_char` / `read_number` (and the whole `run()` call
stack) **untouched**, at the cost of requiring the page to be **cross-origin isolated** (COOP/COEP).
On GitHub Pages — which cannot set headers — cross-origin isolation is supplied by the
**`coi-serviceworker`** shim ([ADR-0008](0008-pyodide-in-browser-for-web-playground.md) deploys
there).

## Considered Options

- **Pre-supplied input textarea** (feed the existing `BufferIO`) — simplest, header-free,
  deterministic, but *not interactive*: you cannot answer a prompt mid-run.
- **Async rewrite of the interpreter's reads** — portable and header-free, but surgery on
  conformance-critical code with real regression risk against the differential harness.
- **JSPI `run_sync`** (WASM stack-switching to await a JS promise without SAB) — no headers, but
  needs very recent Chromium; not yet in Firefox/Safari, so it narrows browser support.
- **`SharedArrayBuffer` + `Atomics.wait`** — chosen. Interpreter untouched, portable across modern
  browsers; the price is cross-origin isolation.

## Consequences

- The page must be **cross-origin isolated**. GitHub Pages can't send COOP/COEP, so
  `coi-serviceworker` registers a service worker that re-serves the page with the headers
  (one first-visit reload). A native-header host (Netlify/Vercel/Cloudflare Pages) is the reversible
  fallback if the shim misbehaves.
- `COEP: require-corp` ⇒ **all assets must be same-origin** (or CORP/`credentialless`), which is why
  ADR-0008 self-hosts the Pyodide dist and wheels. No cross-origin CDN.
- The console is **xterm.js** (+ a local-echo addon). **Ctrl-D** (and a visible button) signals EOF →
  `read_char` returns `-1` (the looping-program EOF carve-out) and `read_number` *raises* (ADR-0001 /
  ADR-0003); the badged error surfaces in the console.
- Examples and share links can carry **canned input**: a read drains a canned queue first (echoed
  into the console for transparency), then blocks on the SAB for live input once the queue empties —
  so the existing `.in` fixtures (`echo`, `primes`, `reverse`, `sierpinski`) are turnkey while free
  exploration stays interactive.
- Cancellation interacts cleanly: `worker.terminate()` tears down a worker blocked in `Atomics.wait`;
  a fresh worker is re-initialised for the next run.
