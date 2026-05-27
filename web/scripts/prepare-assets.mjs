// Prepares all self-hosted assets so the playground is fully same-origin (a COEP
// requirement) and works offline. Run as the `predev`/`prebuild` npm hook.
//
//   1. Build the spl wheel with `uv build --wheel` in the repo root.
//   2. Copy dist/spl-0.1.0-py3-none-any.whl -> public/wheels/ (PEP 427 name preserved;
//      micropip reads name+version from the FILENAME).
//   3. Download lark-1.3.1-py3-none-any.whl from PyPI -> public/wheels/ (so lark is
//      installed from a local wheel at runtime, never fetched from PyPI under COEP).
//   4. Copy the entire node_modules/pyodide dist -> public/pyodide/.
//   4b. The npm pyodide package ships WITHOUT the package wheels (e.g. micropip), which
//       loadPackage would normally fetch from the CDN. For an offline/COEP self-host we
//       download the wheels micropip needs from the version-pinned Pyodide CDN and verify
//       each against the sha256 in pyodide-lock.json.
//   5. Copy coi-serviceworker.js -> public/ for the eventual GitHub Pages deploy.

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const repoRoot = resolve(webRoot, "..");

const SPL_WHEEL = "spl-0.1.0-py3-none-any.whl";
const LARK_VERSION = "1.3.1";
const LARK_WHEEL = `lark-${LARK_VERSION}-py3-none-any.whl`;

// Must match the pinned pyodide npm dep; used to fetch the package wheels the npm
// package omits, from the official version-locked CDN distribution.
const PYODIDE_VERSION = "0.29.4";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full`;
// Pyodide packages we install at runtime via loadPackage and need self-hosted.
const PYODIDE_RUNTIME_PACKAGES = ["micropip"];

const wheelsDir = join(webRoot, "public", "wheels");
const pyodideDir = join(webRoot, "public", "pyodide");
const publicDir = join(webRoot, "public");

mkdirSync(wheelsDir, { recursive: true });

function log(msg) {
  console.log(`[prepare-assets] ${msg}`);
}

// 1. Build the spl wheel in the repo root.
log("building spl wheel via `uv build --wheel`...");
execFileSync("uv", ["build", "--wheel"], { cwd: repoRoot, stdio: "inherit" });

// 2. Copy the spl wheel (keeping its PEP 427 filename).
const splSrc = join(repoRoot, "dist", SPL_WHEEL);
if (!existsSync(splSrc)) {
  throw new Error(`expected ${splSrc} after uv build, but it is missing`);
}
cpSync(splSrc, join(wheelsDir, SPL_WHEEL));
log(`copied ${SPL_WHEEL} -> public/wheels/`);

// 3. Download the lark wheel from PyPI (resolve URL via the JSON API), unless cached.
const larkDest = join(wheelsDir, LARK_WHEEL);
if (existsSync(larkDest)) {
  log(`${LARK_WHEEL} already present; skipping download`);
} else {
  log(`resolving ${LARK_WHEEL} URL from PyPI JSON API...`);
  const metaRes = await fetch(`https://pypi.org/pypi/lark/${LARK_VERSION}/json`);
  if (!metaRes.ok) {
    throw new Error(`PyPI metadata fetch failed: ${metaRes.status} ${metaRes.statusText}`);
  }
  const meta = await metaRes.json();
  const url = meta.urls.find((u) => u.filename === LARK_WHEEL)?.url;
  if (!url) {
    throw new Error(`could not find ${LARK_WHEEL} in PyPI release files`);
  }
  log(`downloading ${url}`);
  const wheelRes = await fetch(url);
  if (!wheelRes.ok) {
    throw new Error(`lark wheel download failed: ${wheelRes.status} ${wheelRes.statusText}`);
  }
  const buf = Buffer.from(await wheelRes.arrayBuffer());
  writeFileSync(larkDest, buf);
  log(`downloaded ${LARK_WHEEL} (${buf.length} bytes) -> public/wheels/`);
}

// 4. Copy the whole Pyodide dist dir (simplest way to get every file it references).
const pyodideSrc = dirname(require.resolve("pyodide"));
rmSync(pyodideDir, { recursive: true, force: true });
cpSync(pyodideSrc, pyodideDir, { recursive: true });
log(`copied pyodide dist from ${pyodideSrc} -> public/pyodide/`);

// 4b. Ensure the runtime package wheels (and their transitive deps) the npm package
// omits are present, fetched from the version-pinned CDN and sha256-verified against
// pyodide-lock.json.
const lock = JSON.parse(readFileSync(join(pyodideDir, "pyodide-lock.json"), "utf8"));
const lockPkgs = lock.packages;

// Resolve the transitive closure of file names + sha256 for each runtime package.
const needed = new Map(); // file_name -> sha256
const visit = (name) => {
  const pkg = lockPkgs[name];
  if (!pkg) throw new Error(`package ${name} not found in pyodide-lock.json`);
  if (needed.has(pkg.file_name)) return;
  needed.set(pkg.file_name, pkg.sha256);
  for (const dep of pkg.depends ?? []) visit(dep);
};
for (const name of PYODIDE_RUNTIME_PACKAGES) visit(name);

for (const [fileName, sha256] of needed) {
  const dest = join(pyodideDir, fileName);
  if (existsSync(dest)) {
    log(`pyodide wheel ${fileName} already present (copied from npm package)`);
    continue;
  }
  const url = `${PYODIDE_CDN}/${fileName}`;
  log(`downloading pyodide wheel ${url}`);
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`pyodide wheel download failed: ${res.status} ${res.statusText} (${url})`);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  const digest = createHash("sha256").update(buf).digest("hex");
  if (digest !== sha256) {
    throw new Error(`sha256 mismatch for ${fileName}: got ${digest}, expected ${sha256}`);
  }
  writeFileSync(dest, buf);
  log(`downloaded ${fileName} (${buf.length} bytes, sha256 verified) -> public/pyodide/`);
}

// 5. Copy coi-serviceworker.js into public/ for the static-host deploy path.
const coiSrc = require.resolve("coi-serviceworker");
cpSync(coiSrc, join(publicDir, "coi-serviceworker.js"));
log(`copied coi-serviceworker.js -> public/`);

// 6. Mirror tests/programs/ into public/examples/ + a manifest so the UI can load any
// program. A program reads input iff it ships a .in (see tests/test_programs.py), so we
// pair each .spl with its optional .in and record the flag. Auto-discovered via *.spl, so
// dropping a new program into tests/programs/ makes it appear in the UI with no code change.
const programsDir = join(repoRoot, "tests", "programs");
const examplesDir = join(publicDir, "examples");
rmSync(examplesDir, { recursive: true, force: true });
mkdirSync(examplesDir, { recursive: true });
const manifest = readdirSync(programsDir)
  .filter((f) => f.endsWith(".spl"))
  .map((f) => f.slice(0, -".spl".length))
  .sort()
  .map((name) => {
    cpSync(join(programsDir, `${name}.spl`), join(examplesDir, `${name}.spl`));
    const inName = `${name}.in`;
    const hasIn = existsSync(join(programsDir, inName));
    if (hasIn) cpSync(join(programsDir, inName), join(examplesDir, inName));
    return { name, spl: `${name}.spl`, in: hasIn ? inName : null, readsInput: hasIn };
  });
writeFileSync(join(examplesDir, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
log(`mirrored ${manifest.length} programs -> public/examples/ (+ manifest.json)`);

// Sanity check: confirm the spl wheel bundles grammar + data files.
const splBytes = readFileSync(join(wheelsDir, SPL_WHEEL));
const hasGrammar = splBytes.includes(Buffer.from("grammar.lark"));
log(`spl wheel bundles grammar.lark: ${hasGrammar}`);

log("done.");
