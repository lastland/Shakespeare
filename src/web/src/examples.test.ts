// Unit tests for examples.ts — manifest parsing + .in pairing. Fetch is stubbed; the
// integration path (real public/examples/manifest.json mirrored from tests/programs/)
// is exercised by Playwright test #5 in e2e/playground.spec.ts.

import { afterEach, describe, expect, it, vi } from "vitest";

import { loadExample, loadManifest, type ExampleMeta } from "./examples";

// Vitest's default `import.meta.env.BASE_URL` is "/", matching Vite dev/preview.
const BASE = "/";

// Map of URL -> response body. Each test installs its own routing.
type Routes = Record<string, { ok: boolean; status?: number; body: string }>;
function stubFetch(routes: Routes) {
  const fetchMock = vi.fn(async (url: string | URL | Request) => {
    const key = String(url);
    const route = routes[key];
    if (!route) {
      throw new Error(`no route stubbed for ${key}`);
    }
    return {
      ok: route.ok,
      status: route.status ?? (route.ok ? 200 : 500),
      statusText: route.ok ? "OK" : "Error",
      text: async () => route.body,
      json: async () => JSON.parse(route.body),
    } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("loadManifest", () => {
  it("returns the parsed manifest array", async () => {
    const manifest: ExampleMeta[] = [
      { name: "hello_world", spl: "hello_world.spl", in: null, readsInput: false },
      { name: "echo", spl: "echo.spl", in: "echo.in", readsInput: true },
    ];
    stubFetch({
      [`${BASE}examples/manifest.json`]: { ok: true, body: JSON.stringify(manifest) },
    });
    await expect(loadManifest()).resolves.toEqual(manifest);
  });

  it("throws on a non-ok response", async () => {
    stubFetch({
      [`${BASE}examples/manifest.json`]: { ok: false, status: 404, body: "" },
    });
    await expect(loadManifest()).rejects.toThrow(/manifest fetch failed: 404/);
  });
});

describe("loadExample", () => {
  it("returns source + cannedInput[.in body] when the program reads input", async () => {
    const meta: ExampleMeta = {
      name: "echo",
      spl: "echo.spl",
      in: "echo.in",
      readsInput: true,
    };
    stubFetch({
      [`${BASE}examples/echo.spl`]: { ok: true, body: "An echo.\n[program]" },
      [`${BASE}examples/echo.in`]: { ok: true, body: "A42\n" },
    });
    await expect(loadExample(meta)).resolves.toEqual({
      source: "An echo.\n[program]",
      cannedInput: ["A42\n"],
    });
  });

  it("returns empty cannedInput when there is no .in", async () => {
    const meta: ExampleMeta = {
      name: "hello_world",
      spl: "hello_world.spl",
      in: null,
      readsInput: false,
    };
    stubFetch({
      [`${BASE}examples/hello_world.spl`]: { ok: true, body: "Hello, World!" },
    });
    await expect(loadExample(meta)).resolves.toEqual({
      source: "Hello, World!",
      cannedInput: [],
    });
  });

  it("throws on a non-ok response", async () => {
    const meta: ExampleMeta = {
      name: "missing",
      spl: "missing.spl",
      in: null,
      readsInput: false,
    };
    stubFetch({
      [`${BASE}examples/missing.spl`]: { ok: false, status: 404, body: "" },
    });
    await expect(loadExample(meta)).rejects.toThrow(/fetch missing\.spl failed: 404/);
  });
});
