// Ambient types for the `window.__spl` test-hook surface that App.tsx exposes for
// Playwright (and dev-time inspection). Used by both src/ and e2e/.

import type { RunnerStatus } from "./runner";

declare global {
  interface Window {
    __spl?: {
      getStatus: () => RunnerStatus;
      examples: {
        helloWorld: string;
        echoProgram: string;
        reverseProgram: string;
        infiniteLoop: string;
      };
      runEcho: () => void;
      runReverse: () => void;
      runInfinite: () => void;
    };
  }
}

export {};
