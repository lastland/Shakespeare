// Main-thread coordinator for the Pyodide worker: owns the SharedArrayBuffer, spawns
// and (on Stop) terminates+respawns the worker, and fulfils synchronous input requests.

import {
  CTRL_LENGTH,
  CTRL_STATUS,
  DATA_BYTES,
  LENGTH_EOF,
  SAB_BYTES,
  STATUS_READY,
  type FromWorker,
} from "./protocol";

export type RunnerStatus = "loading" | "ready" | "running" | "waiting-input";

export interface RunnerCallbacks {
  onStatus(status: RunnerStatus): void;
  onStdout(text: string): void;
  onError(text: string): void;
  onDone(): void;
}

/**
 * Factory for the Pyodide worker. Production passes the default (a thin arrow around the
 * Vite-magic `new Worker(new URL("./worker.ts", import.meta.url), { type: "module" })` so
 * Vite's worker plugin still pattern-matches the literal). Unit tests inject a stub that
 * records postMessage and synthesises `FromWorker` events.
 */
export type WorkerFactory = () => Worker;

const defaultWorkerFactory: WorkerFactory = () =>
  new Worker(new URL("./worker.ts", import.meta.url), { type: "module" });

export class SplRunner {
  private worker: Worker | null = null;
  private sab: SharedArrayBuffer;
  private ctrl: Int32Array;
  private data: Uint8Array;
  private encoder = new TextEncoder();
  private workerFactory: WorkerFactory;

  // Canned input chunks (used to drive examples / tests deterministically). When the
  // queue is empty we fall back to whatever the UI provides via `provideInput`.
  private inputQueue: string[] = [];
  private pendingProvide: ((chunk: string | null) => void) | null = null;
  private awaitingInput = false;

  constructor(private cb: RunnerCallbacks, workerFactory: WorkerFactory = defaultWorkerFactory) {
    this.sab = new SharedArrayBuffer(SAB_BYTES);
    this.ctrl = new Int32Array(this.sab, 0, 2);
    this.data = new Uint8Array(this.sab, 8);
    this.workerFactory = workerFactory;
    this.spawn();
  }

  private spawn() {
    this.cb.onStatus("loading");
    const worker = this.workerFactory();
    worker.onmessage = (ev: MessageEvent<FromWorker>) => this.handle(ev.data);
    worker.onerror = (ev) => this.cb.onError(`worker error: ${ev.message}`);
    worker.postMessage({ type: "init", sab: this.sab });
    this.worker = worker;
  }

  private handle(msg: FromWorker) {
    switch (msg.type) {
      case "ready":
        this.awaitingInput = false;
        this.cb.onStatus("ready");
        break;
      case "stdout":
        this.cb.onStdout(msg.text);
        break;
      case "need-input":
        this.awaitingInput = true;
        this.serveInput();
        break;
      case "done":
        this.awaitingInput = false;
        this.cb.onStatus("ready");
        this.cb.onDone();
        break;
      case "error":
        this.awaitingInput = false;
        this.cb.onError(msg.text);
        this.cb.onStatus("ready");
        break;
    }
  }

  // Decide what to feed the blocked worker. Canned input first; otherwise, surface
  // "waiting-input" and let the UI drive via provideInput/sendEof.
  private serveInput() {
    if (this.inputQueue.length > 0) {
      this.writeInput(this.inputQueue.shift()!);
      return;
    }
    if (this.pendingProvide) {
      // Should not happen, but guard against double-arming.
      return;
    }
    this.cb.onStatus("waiting-input");
  }

  private writeInput(chunk: string) {
    const bytes = this.encoder.encode(chunk);
    if (bytes.length > DATA_BYTES) {
      this.cb.onError(`input chunk too large (${bytes.length} > ${DATA_BYTES} bytes)`);
      return;
    }
    this.data.set(bytes, 0);
    Atomics.store(this.ctrl, CTRL_LENGTH, bytes.length);
    Atomics.store(this.ctrl, CTRL_STATUS, STATUS_READY);
    Atomics.notify(this.ctrl, CTRL_STATUS);
    this.awaitingInput = false;
    this.cb.onStatus("running");
  }

  private writeEof() {
    Atomics.store(this.ctrl, CTRL_LENGTH, LENGTH_EOF);
    Atomics.store(this.ctrl, CTRL_STATUS, STATUS_READY);
    Atomics.notify(this.ctrl, CTRL_STATUS);
    this.awaitingInput = false;
    this.cb.onStatus("running");
  }

  // --- public API used by the UI ------------------------------------------

  run(source: string, cannedInput: string[] = []) {
    this.inputQueue = [...cannedInput];
    this.cb.onStatus("running");
    this.worker?.postMessage({ type: "run", source });
  }

  // Called by the UI's Send button. Only meaningful while waiting for input.
  provideInput(chunk: string) {
    if (!this.awaitingInput) return;
    this.writeInput(chunk);
  }

  // Called by the UI's Send EOF button.
  sendEof() {
    if (!this.awaitingInput) return;
    this.writeEof();
  }

  isAwaitingInput() {
    return this.awaitingInput;
  }

  // Hard cancel: terminate the worker (kills any infinite loop or blocked Atomics.wait)
  // and respawn a fresh one that re-boots Pyodide.
  stop() {
    this.worker?.terminate();
    this.worker = null;
    this.awaitingInput = false;
    this.inputQueue = [];
    // Reset control region so a stale STATUS doesn't confuse the next run.
    Atomics.store(this.ctrl, CTRL_STATUS, 0);
    Atomics.store(this.ctrl, CTRL_LENGTH, 0);
    this.spawn();
  }
}
