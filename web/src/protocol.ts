// Shared protocol between the main thread and the Pyodide worker.

// --- SharedArrayBuffer layout for synchronous input -------------------------
//
//   ctrl: Int32Array view over the first 8 bytes
//     ctrl[0] = STATUS  (0 = worker is waiting, 1 = main has written a reply)
//     ctrl[1] = LENGTH  (>=0: number of UTF-8 bytes in `data`; -1 means EOF)
//   data: Uint8Array view over the remaining bytes (UTF-8 input payload)
//
// The worker, running synchronous Python, blocks on Atomics.wait(ctrl, STATUS, 0).
// The main thread fills `data`, sets LENGTH, stores STATUS=1, and Atomics.notify.

export const CTRL_STATUS = 0;
export const CTRL_LENGTH = 1;

export const STATUS_WAITING = 0;
export const STATUS_READY = 1;

export const LENGTH_EOF = -1;

export const CTRL_BYTES = 8; // two Int32 slots
export const DATA_BYTES = 64 * 1024; // 64 KiB UTF-8 input region
export const SAB_BYTES = CTRL_BYTES + DATA_BYTES;

// --- Messages ---------------------------------------------------------------

// main -> worker
export type ToWorker =
  | { type: "init"; sab: SharedArrayBuffer }
  | { type: "run"; source: string };

// worker -> main
export type FromWorker =
  | { type: "ready" } // pyodide + packages loaded, idle
  | { type: "need-input" } // Python called request(); main must fill the SAB
  | { type: "stdout"; text: string }
  | { type: "done" } // program finished normally
  | { type: "error"; text: string };
