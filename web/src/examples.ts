// The example gallery, mirrored from tests/programs/ by scripts/prepare-assets.mjs into
// public/examples/ (manifest.json + the .spl/.in files). Everything is same-origin under
// BASE_URL, so it loads under COEP and works offline. Fetched lazily: the manifest up
// front, each program's source/input only when selected.

const BASE = import.meta.env.BASE_URL;

export interface ExampleMeta {
  /** Filename stem, e.g. "hello_world" — also the dropdown label. */
  name: string;
  /** Source filename under examples/, e.g. "hello_world.spl". */
  spl: string;
  /** Stdin fixture filename, or null when the program reads no input. */
  in: string | null;
  /** True iff the program ships a .in (i.e. reads input). */
  readsInput: boolean;
}

export interface LoadedExample {
  source: string;
  /**
   * The .in contents as a single canned-input chunk (or [] when none). Fed to
   * SplRunner.run as the canned queue, which is consumed before the runner falls back to
   * interactive prompting (ADR-0009 / Q10) — so EOF-terminated readers (echo, reverse)
   * still need a manual Send EOF to finish.
   */
  cannedInput: string[];
}

async function fetchText(path: string): Promise<string> {
  const res = await fetch(`${BASE}examples/${path}`);
  if (!res.ok) throw new Error(`fetch ${path} failed: ${res.status} ${res.statusText}`);
  return res.text();
}

export async function loadManifest(): Promise<ExampleMeta[]> {
  const res = await fetch(`${BASE}examples/manifest.json`);
  if (!res.ok) throw new Error(`manifest fetch failed: ${res.status} ${res.statusText}`);
  return res.json() as Promise<ExampleMeta[]>;
}

export async function loadExample(meta: ExampleMeta): Promise<LoadedExample> {
  const source = await fetchText(meta.spl);
  const cannedInput = meta.in ? [await fetchText(meta.in)] : [];
  return { source, cannedInput };
}
