import { useCallback, useEffect, useRef, useState } from "react";
import { SplRunner, type RunnerStatus } from "./runner";
import helloWorld from "./hello_world.spl.txt?raw";
import echoProgram from "./echo.spl.txt?raw";
import reverseProgram from "./reverse.spl.txt?raw";

// A trivial always-looping SPL program for the Stop test: Romeo repeatedly remembers
// himself, so the interpreter never terminates (no I/O, no exit condition).
const INFINITE_LOOP = `An infinite loop.
Romeo, a man.
Juliet, a woman.
        Act I: Loop.
        Scene I: Forever.
[Enter Romeo and Juliet]
Juliet: You are nothing. Are you better than nothing?
Romeo: If so, let us return to Scene I.
[Exeunt]
`;

const STATUS_LABEL: Record<RunnerStatus, string> = {
  loading: "Loading Pyodide + interpreter...",
  ready: "Ready.",
  running: "Running...",
  "waiting-input": "Waiting for input (type below, then Send, or Send EOF).",
};

export default function App() {
  const [source, setSource] = useState(helloWorld);
  const [output, setOutput] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState<RunnerStatus>("loading");
  const [inputValue, setInputValue] = useState("");
  const runnerRef = useRef<SplRunner | null>(null);

  useEffect(() => {
    const runner = new SplRunner({
      onStatus: setStatus,
      onStdout: (text) => setOutput((prev) => prev + text),
      onError: (text) => setError((prev) => prev + text),
      onDone: () => {},
    });
    runnerRef.current = runner;
    // No teardown: a single runner lives for the page lifetime; Stop terminates+respawns
    // its worker internally.
  }, []);

  const handleRun = useCallback(
    (overrideSource?: string, cannedInput?: string[]) => {
      setOutput("");
      setError("");
      const src = overrideSource ?? source;
      runnerRef.current?.run(src, cannedInput);
    },
    [source],
  );

  const handleStop = useCallback(() => {
    runnerRef.current?.stop();
    setError("");
  }, []);

  const handleSend = useCallback(() => {
    // Send the textbox content as one chunk. The echo/looping protocol expects the
    // user to include any newline themselves (e.g. "A42\n").
    runnerRef.current?.provideInput(inputValue);
    setInputValue("");
  }, [inputValue]);

  const handleEof = useCallback(() => {
    runnerRef.current?.sendEof();
  }, []);

  // Test hooks: expose helpers + raw example sources to Playwright on window.
  useEffect(() => {
    (window as any).__spl = {
      getStatus: () => status,
      examples: { helloWorld, echoProgram, reverseProgram, infiniteLoop: INFINITE_LOOP },
      runEcho: () => {
        setSource(echoProgram);
        handleRun(echoProgram);
      },
      runReverse: () => {
        setSource(reverseProgram);
        handleRun(reverseProgram);
      },
      runInfinite: () => {
        setSource(INFINITE_LOOP);
        handleRun(INFINITE_LOOP);
      },
    };
  }, [status, handleRun]);

  return (
    <div style={{ fontFamily: "monospace", padding: "1rem", maxWidth: 900 }}>
      <h1>SPL Playground (scaffold)</h1>

      <div id="status" data-status={status} style={{ margin: "0.5rem 0", fontWeight: "bold" }}>
        {STATUS_LABEL[status]}
      </div>

      <textarea
        id="source"
        value={source}
        onChange={(e) => setSource(e.target.value)}
        rows={14}
        style={{ width: "100%", fontFamily: "monospace" }}
      />

      <div style={{ margin: "0.5rem 0", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button id="run" onClick={() => handleRun()} disabled={status === "loading"}>
          Run
        </button>
        <button id="stop" onClick={handleStop}>
          Stop
        </button>
        <button id="load-echo" onClick={() => setSource(echoProgram)}>
          Load echo example
        </button>
      </div>

      <div style={{ margin: "0.5rem 0", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <input
          id="stdin"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="program input (include \n yourself)"
          style={{ fontFamily: "monospace", minWidth: 240 }}
        />
        <button id="send" onClick={handleSend}>
          Send
        </button>
        <button id="send-eof" onClick={handleEof}>
          Send EOF (Ctrl-D)
        </button>
      </div>

      <h3>Output</h3>
      <pre
        id="output"
        style={{
          background: "#111",
          color: "#0f0",
          padding: "0.5rem",
          minHeight: "4rem",
          whiteSpace: "pre-wrap",
          overflowX: "auto",
        }}
      >
        {output}
      </pre>

      <h3>Errors</h3>
      <pre
        id="error"
        style={{
          background: "#200",
          color: "#f88",
          padding: "0.5rem",
          minHeight: "2rem",
          whiteSpace: "pre-wrap",
        }}
      >
        {error}
      </pre>
    </div>
  );
}
