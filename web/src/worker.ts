/// <reference lib="webworker" />
//
// Pyodide worker. Boots Pyodide from the self-hosted /pyodide/ dir, installs the
// lark + spl wheels from the in-FS /wheels/ dir (offline, COEP-safe), and runs SPL
// programs. Synchronous Python input is satisfied by blocking on a SharedArrayBuffer
// via Atomics.wait; the main thread fills the buffer in response to `need-input`.

import {
  CTRL_LENGTH,
  CTRL_STATUS,
  LENGTH_EOF,
  STATUS_WAITING,
  type FromWorker,
  type ToWorker,
} from "./protocol";

interface PyodideInterface {
  loadPackage(names: string | string[]): Promise<void>;
  pyimport(name: string): any;
  runPython(code: string): any;
  FS: { writeFile(path: string, data: Uint8Array): void; mkdirTree(path: string): void };
  globals: { get(name: string): any };
}

// This is a module worker, so importScripts is unavailable. Dynamically import the
// self-hosted ESM build at its runtime URL (/pyodide/), keeping everything same-origin
// (a COEP requirement). The bare runtime URL is hidden from Vite's bundler via a
// computed specifier so it is not rewritten or pre-bundled.
async function loadPyodideModule(): Promise<
  (opts: { indexURL: string }) => Promise<PyodideInterface>
> {
  const url = "/pyodide/" + "pyodide.mjs";
  const mod = await import(/* @vite-ignore */ url);
  return mod.loadPyodide;
}

function post(msg: FromWorker) {
  (self as unknown as Worker).postMessage(msg);
}

let ctrl: Int32Array | null = null;
let data: Uint8Array | null = null;
const decoder = new TextDecoder();

// Synchronous input: block until the main thread fills the SAB. Returns the decoded
// chunk, or null at EOF (which the Python WorkerInput shim maps to "" -> StdIO EOF).
function requestInputSync(): string | null {
  if (!ctrl || !data) {
    throw new Error("worker: SharedArrayBuffer not initialized");
  }
  Atomics.store(ctrl, CTRL_STATUS, STATUS_WAITING);
  post({ type: "need-input" });
  // Block this worker thread until the main thread stores STATUS_READY and notifies.
  Atomics.wait(ctrl, CTRL_STATUS, STATUS_WAITING);
  const length = Atomics.load(ctrl, CTRL_LENGTH);
  if (length === LENGTH_EOF) {
    return null;
  }
  // TextDecoder refuses views backed by a SharedArrayBuffer, so copy the payload into a
  // plain (non-shared) Uint8Array first.
  const bytes = new Uint8Array(length);
  bytes.set(data.subarray(0, length));
  return decoder.decode(bytes);
}

let runProgram: ((src: string, request: () => string | null, emit: (s: string) => void) => void) | null =
  null;

async function boot() {
  const loadPyodide = await loadPyodideModule();
  const pyodide = await loadPyodide({ indexURL: "/pyodide/" });
  await pyodide.loadPackage("micropip");

  // Install lark + spl from local wheels written into the Pyodide FS. micropip reads
  // name/version from the PEP 427 filename, so we keep the real names.
  pyodide.FS.mkdirTree("/wheels");
  for (const name of ["lark-1.3.1-py3-none-any.whl", "spl-0.1.0-py3-none-any.whl"]) {
    const res = await fetch(`/wheels/${name}`);
    if (!res.ok) throw new Error(`failed to fetch wheel ${name}: ${res.status}`);
    pyodide.FS.writeFile(`/wheels/${name}`, new Uint8Array(await res.arrayBuffer()));
  }
  const micropip = pyodide.pyimport("micropip");
  await micropip.install("emfs:/wheels/lark-1.3.1-py3-none-any.whl");
  await micropip.install("emfs:/wheels/spl-0.1.0-py3-none-any.whl");

  // The IO shims (from the proven proof.mjs): WorkerInput.read(1) pulls blocking chunks
  // from a JS \`request\` callback (chunk str, or EOF) and feeds the existing
  // StdIO/_CharReader so read_number/read_char semantics stay UNCHANGED. WorkerOutput
  // streams each write to a JS \`emit\` callback.
  //
  // EOF check note: in a browser worker, Pyodide 0.29 wraps a returned JS \`null\` as a
  // JsNull proxy rather than Python None (unlike Node, where proof.mjs saw None), so
  // \`chunk is None\` would miss it and \`len(chunk)\` would raise. A real input chunk is
  // always a str; anything else (JsNull/JsUndefined/None) means EOF. Testing \`isinstance
  // str\` is conversion-agnostic and preserves the proof's chunk-or-EOF semantics exactly.
  pyodide.runPython(`
from spl.backend.io import StdIO
from spl.frontend.parser import parse
from spl.backend.analyzer import analyze
from spl.backend.interpreter import Interpreter

class WorkerInput:
    def __init__(self, request):
        self._buf = ""; self._pos = 0; self._eof = False; self._request = request
    def read(self, n=1):
        while self._pos >= len(self._buf):
            if self._eof:
                return ""
            chunk = self._request()
            if not isinstance(chunk, str):
                self._eof = True
                return ""
            self._buf = chunk; self._pos = 0
        ch = self._buf[self._pos]; self._pos += 1
        return ch

class WorkerOutput:
    def __init__(self, emit): self._emit = emit
    def write(self, s): self._emit(s)
    def flush(self): pass

def run_program(src, request, emit):
    io = StdIO(input=WorkerInput(request), output=WorkerOutput(emit))
    Interpreter(analyze(parse(src)), io=io).run()
`);

  runProgram = pyodide.globals.get("run_program");
  post({ type: "ready" });
}

const bootPromise = boot().catch((err) => {
  post({ type: "error", text: `worker boot failed: ${err?.message ?? String(err)}` });
  throw err;
});

self.onmessage = async (ev: MessageEvent<ToWorker>) => {
  const msg = ev.data;
  if (msg.type === "init") {
    ctrl = new Int32Array(msg.sab, 0, 2);
    data = new Uint8Array(msg.sab, 8);
    return;
  }
  if (msg.type === "run") {
    await bootPromise;
    if (!runProgram) {
      post({ type: "error", text: "worker: interpreter not initialized" });
      return;
    }
    try {
      const emit = (s: string) => post({ type: "stdout", text: s });
      runProgram(msg.source, requestInputSync, emit);
      post({ type: "done" });
    } catch (err: any) {
      // PythonError (and anything else) surfaces here; forward its message.
      post({ type: "error", text: err?.message ?? String(err) });
    }
  }
};
