import { useCallback, useEffect, useRef, useState } from "react";
import { SplRunner, type RunnerStatus } from "./runner";
import { loadExample, loadManifest, type ExampleMeta } from "./examples";
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
  const [examples, setExamples] = useState<ExampleMeta[]>([]);
  const [selectedName, setSelectedName] = useState("hello_world");
  const runnerRef = useRef<SplRunner | null>(null);
  // Canned input of the currently-loaded example (its .in), fed to run() when the user
  // clicks Run. Cleared on manual source edits so it never applies to hand-written code.
  const cannedInputRef = useRef<string[]>([]);

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

  // Populate the gallery dropdown from the manifest mirrored from tests/programs/.
  useEffect(() => {
    loadManifest()
      .then(setExamples)
      .catch((e) => setError(`failed to load examples: ${e.message}`));
  }, []);

  const handleRun = useCallback(
    (overrideSource?: string, cannedInput?: string[]) => {
      setOutput("");
      setError("");
      const src = overrideSource ?? source;
      runnerRef.current?.run(src, cannedInput ?? cannedInputRef.current);
    },
    [source],
  );

  // Load the selected program's source + its .in (as canned input) without running.
  const handleSelectExample = useCallback(
    (name: string) => {
      setSelectedName(name);
      if (name === "") return;
      const meta = examples.find((ex) => ex.name === name);
      if (!meta) return;
      setError("");
      loadExample(meta)
        .then(({ source: src, cannedInput }) => {
          setSource(src);
          cannedInputRef.current = cannedInput;
        })
        .catch((e) => setError(`failed to load ${name}: ${e.message}`));
    },
    [examples],
  );

  // A manual edit makes the buffer no-longer-an-example: drop its canned input and the
  // dropdown selection so a later Run won't feed stale stdin.
  const handleSourceChange = useCallback((value: string) => {
    setSource(value);
    cannedInputRef.current = [];
    setSelectedName("");
  }, []);

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
      // Plumbing tests drive input via Send/SendEof, never canned input -> pass [] so any
      // dropdown selection state cannot leak into the SAB-handshake assertions.
      runEcho: () => {
        setSource(echoProgram);
        handleRun(echoProgram, []);
      },
      runReverse: () => {
        setSource(reverseProgram);
        handleRun(reverseProgram, []);
      },
      runInfinite: () => {
        setSource(INFINITE_LOOP);
        handleRun(INFINITE_LOOP, []);
      },
    };
  }, [status, handleRun]);

  return (
    <div className="app">
      <h1>SPL Playground (scaffold)</h1>

      <div id="status" data-status={status} className="status" role="status">
        {STATUS_LABEL[status]}
      </div>

      <div className="controls">
        <label htmlFor="example-select">Load a program from tests/programs/:</label>
        <select
          id="example-select"
          className="select"
          value={selectedName}
          onChange={(e) => handleSelectExample(e.target.value)}
          disabled={status === "loading" || examples.length === 0}
        >
          <option value="">— choose —</option>
          {examples.map((ex) => (
            <option key={ex.name} value={ex.name}>
              {ex.name}
              {ex.readsInput ? " (reads input)" : ""}
            </option>
          ))}
        </select>
      </div>

      <textarea
        id="source"
        className="editor"
        aria-label="SPL program source"
        value={source}
        onChange={(e) => handleSourceChange(e.target.value)}
        rows={14}
      />

      <div className="actions">
        <button id="run" className="btn btn--primary" onClick={() => handleRun()} disabled={status === "loading"}>
          Run
        </button>
        <button id="stop" className="btn btn--secondary" onClick={handleStop}>
          Stop
        </button>
      </div>

      <div className="actions">
        <input
          id="stdin"
          className="text-input"
          aria-label="Program input"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="program input (include \n yourself)"
        />
        <button id="send" className="btn btn--secondary" onClick={handleSend}>
          Send
        </button>
        <button id="send-eof" className="btn btn--secondary" onClick={handleEof}>
          Send EOF (Ctrl-D)
        </button>
      </div>

      <h2 className="section-label">Output</h2>
      <pre id="output" className="panel panel--output" aria-live="polite">
        {output}
      </pre>

      <h2 className="section-label">Errors</h2>
      <pre id="error" className="panel panel--error" role="alert">
        {error}
      </pre>
    </div>
  );
}
