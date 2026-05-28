import { expect, test } from "@playwright/test";

// End-to-end proof of the risky browser plumbing for the SPL playground:
//   1. COOP/COEP -> crossOriginIsolated === true (prerequisite for SAB + Atomics).
//   2. Pyodide boots, installs the local lark + spl wheels, and runs hello_world.
//   3. Synchronous interactive input round-trip via SharedArrayBuffer + Atomics.
//   4. Stop = worker terminate + respawn, and a subsequent Run still works.

const READY = "Ready.";

async function waitForReady(page: import("@playwright/test").Page) {
  await expect(page.locator("#status")).toHaveAttribute("data-status", "ready", {
    timeout: 90_000,
  });
}

test.describe("SPL playground scaffold", () => {
  test("1. crossOriginIsolated is true (COOP/COEP wired)", async ({ page }) => {
    await page.goto("/");
    const isolated = await page.evaluate(() => crossOriginIsolated);
    expect(isolated).toBe(true);
  });

  test("2. hello_world runs and prints Hello World!", async ({ page }) => {
    await page.goto("/");
    expect(await page.evaluate(() => crossOriginIsolated)).toBe(true);
    await waitForReady(page);

    await page.locator("#run").click();
    await expect(page.locator("#output")).toContainText("Hello World!", {
      timeout: 60_000,
    });
    await expect(page.locator("#error")).toHaveText("");
  });

  test("3a. interactive echo round-trip (multi-chunk SAB + Atomics)", async ({ page }) => {
    await page.goto("/");
    expect(await page.evaluate(() => crossOriginIsolated)).toBe(true);
    await waitForReady(page);

    // echo.spl performs three reads: read char -> write char; read number -> write
    // number; read char -> write char. Splitting input across TWO chunks ("A42\n" then
    // "Z") forces TWO synchronous SAB round-trips, proving the Atomics handshake works
    // repeatedly. Proven output: "A42Z".
    await page.evaluate(() => (window as any).__spl.runEcho());

    await expect(page.locator("#status")).toHaveAttribute("data-status", "waiting-input", {
      timeout: 60_000,
    });
    await page.locator("#stdin").fill("A42\n");
    await page.locator("#send").click();

    // The final read_char needs another chunk -> a second round-trip.
    await expect(page.locator("#status")).toHaveAttribute("data-status", "waiting-input", {
      timeout: 60_000,
    });
    await page.locator("#stdin").fill("Z");
    await page.locator("#send").click();

    await expect(page.locator("#output")).toContainText("A42Z", { timeout: 60_000 });
    await expect(page.locator("#error")).toHaveText("");
  });

  test("3b. Send EOF button terminates input (reverse.spl)", async ({ page }) => {
    await page.goto("/");
    expect(await page.evaluate(() => crossOriginIsolated)).toBe(true);
    await waitForReady(page);

    // reverse.spl reads characters until EOF, then writes them back reversed. With input
    // "Hello" followed by EOF, the proven output is "olleH". This exercises the Send EOF
    // (Ctrl-D) button: the program requests once for "Hello", then requests again where
    // EOF (length = -1 in the SAB) is the natural terminator.
    await page.evaluate(() => (window as any).__spl.runReverse());

    await expect(page.locator("#status")).toHaveAttribute("data-status", "waiting-input", {
      timeout: 60_000,
    });
    await page.locator("#stdin").fill("Hello");
    await page.locator("#send").click();

    await expect(page.locator("#status")).toHaveAttribute("data-status", "waiting-input", {
      timeout: 60_000,
    });
    await page.locator("#send-eof").click();

    await expect(page.locator("#output")).toContainText("olleH", { timeout: 60_000 });
    await expect(page.locator("#error")).toHaveText("");
  });

  test("4. Stop terminates+respawns; a subsequent Run still works", async ({ page }) => {
    await page.goto("/");
    expect(await page.evaluate(() => crossOriginIsolated)).toBe(true);
    await waitForReady(page);

    // Start an infinite-loop SPL program, confirm it is running, then Stop.
    await page.evaluate(() => (window as any).__spl.runInfinite());
    await expect(page.locator("#status")).toHaveAttribute("data-status", "running", {
      timeout: 30_000,
    });

    await page.locator("#stop").click();
    // Respawn re-boots Pyodide: loading -> ready.
    await waitForReady(page);

    // A fresh Run of hello_world must still work after terminate+respawn.
    await page.locator("#source").fill((await page.evaluate(() => (window as any).__spl.examples.helloWorld)));
    await page.locator("#run").click();
    await expect(page.locator("#output")).toContainText("Hello World!", {
      timeout: 60_000,
    });

    await page.screenshot({ path: "e2e/artifacts/after-stop-rerun.png", fullPage: true });
  });

  test("5. gallery: load a program from the manifest dropdown and run it", async ({ page }) => {
    await page.goto("/");
    await waitForReady(page);

    // The dropdown is populated from public/examples/manifest.json (mirrored from
    // tests/programs/). It should hold the placeholder + the 8 programs.
    await expect
      .poll(async () => page.locator("#example-select option").count(), { timeout: 30_000 })
      .toBeGreaterThan(1);

    // greeting.spl reads no input and its golden output is "HI": picking it must populate
    // the editor (source fetched from the manifest) and a Run must print the golden.
    await page.selectOption("#example-select", "greeting");
    await expect(page.locator("#source")).not.toHaveValue("");
    await page.locator("#run").click();
    await expect(page.locator("#output")).toContainText("HI", { timeout: 60_000 });
    await expect(page.locator("#error")).toHaveText("");
  });
});
