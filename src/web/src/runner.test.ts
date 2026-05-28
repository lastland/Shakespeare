// Unit tests for SplRunner — the main-thread coordinator. Exercised here without a real
// Pyodide worker: we inject a FakeWorker via the `workerFactory` ctor seam, run a real
// SharedArrayBuffer + Atomics (both native in Node), and assert on the SAB contents,
// callback sequence, and worker postMessage stream. Pyodide-integrated paths stay covered
// by the Playwright e2e suite in e2e/playground.spec.ts.

import { describe, expect, it, vi } from "vitest";

import {
  CTRL_LENGTH,
  CTRL_STATUS,
  DATA_BYTES,
  LENGTH_EOF,
  STATUS_READY,
  type FromWorker,
  type ToWorker,
} from "./protocol";
import { SplRunner, type WorkerFactory } from "./runner";

class FakeWorker {
  posted: ToWorker[] = [];
  terminated = false;
  onmessage: ((ev: MessageEvent<FromWorker>) => void) | null = null;
  onerror: ((ev: ErrorEvent) => void) | null = null;

  postMessage(msg: ToWorker) {
    this.posted.push(msg);
  }
  terminate() {
    this.terminated = true;
  }
  // Test helper: synthesise a worker -> main message.
  emit(msg: FromWorker) {
    this.onmessage?.({ data: msg } as MessageEvent<FromWorker>);
  }
}

interface TestHarness {
  runner: SplRunner;
  workers: FakeWorker[];
  cb: {
    onStatus: ReturnType<typeof vi.fn>;
    onStdout: ReturnType<typeof vi.fn>;
    onError: ReturnType<typeof vi.fn>;
    onDone: ReturnType<typeof vi.fn>;
  };
}

function harness(): TestHarness {
  const workers: FakeWorker[] = [];
  const factory: WorkerFactory = () => {
    const w = new FakeWorker();
    workers.push(w);
    return w as unknown as Worker;
  };
  const cb = {
    onStatus: vi.fn(),
    onStdout: vi.fn(),
    onError: vi.fn(),
    onDone: vi.fn(),
  };
  const runner = new SplRunner(cb, factory);
  return { runner, workers, cb };
}

// The init postMessage from spawn() carries the SAB; pull it out so tests can inspect
// what runner.ts writes into the control + data regions.
function sabViews(worker: FakeWorker) {
  const init = worker.posted[0];
  if (!init || init.type !== "init") {
    throw new Error(`expected init message, got ${JSON.stringify(init)}`);
  }
  const sab = init.sab;
  return {
    sab,
    ctrl: new Int32Array(sab, 0, 2),
    data: new Uint8Array(sab, 8),
  };
}

describe("SplRunner — lifecycle + status", () => {
  it("posts init with a SharedArrayBuffer on spawn and reports 'loading'", () => {
    const { workers, cb } = harness();
    expect(workers).toHaveLength(1);
    expect(workers[0].posted[0]).toMatchObject({ type: "init" });
    expect((workers[0].posted[0] as { sab: SharedArrayBuffer }).sab).toBeInstanceOf(
      SharedArrayBuffer,
    );
    expect(cb.onStatus).toHaveBeenCalledWith("loading");
  });

  it("transitions to 'ready' on the worker's ready message", () => {
    const { workers, cb } = harness();
    workers[0].emit({ type: "ready" });
    expect(cb.onStatus).toHaveBeenLastCalledWith("ready");
  });

  it("forwards stdout chunks via onStdout", () => {
    const { workers, cb } = harness();
    workers[0].emit({ type: "stdout", text: "Hello " });
    workers[0].emit({ type: "stdout", text: "World!" });
    expect(cb.onStdout).toHaveBeenNthCalledWith(1, "Hello ");
    expect(cb.onStdout).toHaveBeenNthCalledWith(2, "World!");
  });

  it("reports onDone + 'ready' when the worker signals done", () => {
    const { workers, cb } = harness();
    workers[0].emit({ type: "done" });
    expect(cb.onDone).toHaveBeenCalledOnce();
    expect(cb.onStatus).toHaveBeenLastCalledWith("ready");
  });

  it("forwards worker errors via onError + 'ready'", () => {
    const { workers, cb } = harness();
    workers[0].emit({ type: "error", text: "boom" });
    expect(cb.onError).toHaveBeenCalledWith("boom");
    expect(cb.onStatus).toHaveBeenLastCalledWith("ready");
  });
});

describe("SplRunner — run() + canned input", () => {
  it("posts a run message and drains the canned queue on each need-input", () => {
    const { runner, workers, cb } = harness();
    const w = workers[0];
    runner.run("the play", ["A42\n", "Z"]);
    expect(w.posted).toContainEqual({ type: "run", source: "the play" });

    const { ctrl, data } = sabViews(w);
    const decoder = new TextDecoder();

    // First need-input -> first queued chunk written to SAB.
    w.emit({ type: "need-input" });
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(4); // "A42\n" = 4 UTF-8 bytes
    expect(Atomics.load(ctrl, CTRL_STATUS)).toBe(STATUS_READY);
    expect(decoder.decode(data.subarray(0, 4))).toBe("A42\n");
    expect(cb.onStatus).toHaveBeenLastCalledWith("running");

    // Second need-input -> second queued chunk.
    w.emit({ type: "need-input" });
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(1);
    expect(decoder.decode(data.subarray(0, 1))).toBe("Z");

    // Third need-input -> queue empty, transitions to 'waiting-input'.
    w.emit({ type: "need-input" });
    expect(cb.onStatus).toHaveBeenLastCalledWith("waiting-input");
  });

  it("encodes UTF-8 multibyte chunks correctly", () => {
    const { runner, workers } = harness();
    const w = workers[0];
    runner.run("src", ["héllo"]); // é = 0xC3 0xA9 (2 bytes)
    w.emit({ type: "need-input" });
    const { ctrl, data } = sabViews(w);
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(6);
    expect(new TextDecoder().decode(data.subarray(0, 6))).toBe("héllo");
  });
});

describe("SplRunner — provideInput / sendEof guards", () => {
  it("provideInput is a no-op outside waiting-input", () => {
    const { runner, workers } = harness();
    const w = workers[0];
    const { ctrl } = sabViews(w);
    Atomics.store(ctrl, CTRL_STATUS, 99); // sentinel: should not be overwritten

    runner.provideInput("x");
    expect(Atomics.load(ctrl, CTRL_STATUS)).toBe(99);
    expect(runner.isAwaitingInput()).toBe(false);
  });

  it("provideInput writes the chunk while awaiting input", () => {
    const { runner, workers } = harness();
    const w = workers[0];
    runner.run("src");
    w.emit({ type: "need-input" }); // empty canned queue -> waiting-input
    expect(runner.isAwaitingInput()).toBe(true);

    runner.provideInput("hi");
    const { ctrl, data } = sabViews(w);
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(2);
    expect(Atomics.load(ctrl, CTRL_STATUS)).toBe(STATUS_READY);
    expect(new TextDecoder().decode(data.subarray(0, 2))).toBe("hi");
    expect(runner.isAwaitingInput()).toBe(false);
  });

  it("sendEof writes LENGTH_EOF while awaiting; no-op otherwise", () => {
    const { runner, workers, cb } = harness();
    const w = workers[0];
    const { ctrl } = sabViews(w);

    // No-op before awaiting.
    runner.sendEof();
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(0);

    // Arm + fire.
    runner.run("src");
    w.emit({ type: "need-input" });
    expect(runner.isAwaitingInput()).toBe(true);

    runner.sendEof();
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(LENGTH_EOF);
    expect(Atomics.load(ctrl, CTRL_STATUS)).toBe(STATUS_READY);
    expect(cb.onStatus).toHaveBeenLastCalledWith("running");
    expect(runner.isAwaitingInput()).toBe(false);
  });

  it("rejects an oversized chunk via onError and leaves the SAB unwritten", () => {
    const { runner, workers, cb } = harness();
    const w = workers[0];
    runner.run("src");
    w.emit({ type: "need-input" });

    const tooBig = "x".repeat(DATA_BYTES + 1);
    const { ctrl } = sabViews(w);
    const lenBefore = Atomics.load(ctrl, CTRL_LENGTH);
    const statusBefore = Atomics.load(ctrl, CTRL_STATUS);

    runner.provideInput(tooBig);
    expect(cb.onError).toHaveBeenCalledWith(expect.stringContaining("input chunk too large"));
    // SAB ctrl untouched on rejection.
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(lenBefore);
    expect(Atomics.load(ctrl, CTRL_STATUS)).toBe(statusBefore);
  });
});

describe("SplRunner — stop()", () => {
  it("terminates the current worker, resets ctrl, and respawns a fresh worker", () => {
    const { runner, workers, cb } = harness();
    const w0 = workers[0];
    const { ctrl } = sabViews(w0);

    // Dirty the control region so we can prove stop() resets it.
    Atomics.store(ctrl, CTRL_STATUS, STATUS_READY);
    Atomics.store(ctrl, CTRL_LENGTH, 42);

    runner.stop();

    expect(w0.terminated).toBe(true);
    expect(Atomics.load(ctrl, CTRL_STATUS)).toBe(0);
    expect(Atomics.load(ctrl, CTRL_LENGTH)).toBe(0);
    expect(workers).toHaveLength(2);
    expect(workers[1].posted[0]).toMatchObject({ type: "init" });
    // 'loading' is fired again on respawn.
    expect(cb.onStatus).toHaveBeenLastCalledWith("loading");
  });

  it("drops any canned input queued before stop", () => {
    const { runner, workers, cb } = harness();
    const w0 = workers[0];
    runner.run("first", ["A", "B"]); // arm the queue

    runner.stop();
    const w1 = workers[1];
    runner.run("second"); // no canned input this time
    w1.emit({ type: "need-input" }); // queue should be empty -> waiting-input
    expect(cb.onStatus).toHaveBeenLastCalledWith("waiting-input");

    // The new worker received its own run message — proves we didn't reuse w0.
    expect(w0.posted).toContainEqual({ type: "run", source: "first" });
    expect(w1.posted).toContainEqual({ type: "run", source: "second" });
  });
});
