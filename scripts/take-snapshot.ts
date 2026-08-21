#!/usr/bin/env -S npx tsx
/**
 * Visual snapshot tool - part of HostHub's visual memory protocol
 * (see docs/VISUAL_EVOLUTION.md).
 *
 * Captures a full-page screenshot of a given route and stores it under
 * docs/screenshots/<label>/<timestamp>.png. Screenshots for the same label are kept
 * side by side chronologically, so `ls docs/screenshots/<label>` gives an evolution
 * history for that screen - the two most recent files are the "antes"/"depois" pair
 * for whatever just changed.
 *
 * Usage:
 *   npm run snapshot -- <label> <path> [options]
 *   npx tsx scripts/take-snapshot.ts <label> <path> [options]
 *
 * Required:
 *   <label>                 Slug identifying the screen (e.g. "app-dashboard", "admin-instances")
 *   <path>                  Route to capture, relative to --base (e.g. "/app")
 *
 * Options:
 *   --base=<url>            Base URL to navigate against (default: http://localhost:8888)
 *   --viewport=<WxH>        Viewport size in CSS pixels (default: 1440x900)
 *   --email=<email>         Login email. Combined with --password, logs in via
 *                           POST {base}/api/v1/auth/login before navigating, so protected
 *                           routes (/app, /admin) render with real data instead of the login
 *                           screen.
 *   --password=<password>
 *   --full-page=false       Capture only the viewport instead of the full scrollable page
 *   --settle-ms=<n>         Extra wait after navigation, for motion/animations to settle
 *                           (default: 800)
 *
 * Output (stdout): the previous screenshot's path for this label (if any, prefixed
 * "PREVIOUS: "), then the newly saved screenshot's absolute path on the last line.
 */
import { mkdir, readdir } from "node:fs/promises";
import path from "node:path";
import puppeteer from "puppeteer";

function parseArgs(argv: string[]) {
  const positional: string[] = [];
  const flags: Record<string, string> = {};
  for (const arg of argv) {
    if (arg.startsWith("--")) {
      const [key, ...rest] = arg.slice(2).split("=");
      flags[key] = rest.join("=") || "true";
    } else {
      positional.push(arg);
    }
  }
  return { positional, flags };
}

/** Logs in against the API and returns the raw Set-Cookie headers (hh_access/hh_refresh) so
 * they can be attached to the puppeteer page before navigating to a protected route. */
async function loginCookies(base: string, email: string, password: string): Promise<string[]> {
  const response = await fetch(`${base}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error(`Login failed for ${email}: HTTP ${response.status}`);
  }
  const setCookie = response.headers.getSetCookie?.() ?? [];
  if (setCookie.length === 0) {
    throw new Error("Login succeeded but the response had no Set-Cookie headers");
  }
  return setCookie;
}

async function main() {
  const { positional, flags } = parseArgs(process.argv.slice(2));
  const [label, routePath] = positional;
  if (!label || !routePath) {
    console.error(
      "Usage: take-snapshot.ts <label> <path> [--base=] [--viewport=WxH] [--email=] [--password=] [--full-page=false] [--settle-ms=]"
    );
    process.exit(1);
  }

  const base = flags.base ?? "http://localhost:8888";
  const [width, height] = (flags.viewport ?? "1440x900").split("x").map(Number);
  const fullPage = flags["full-page"] !== "false";
  const settleMs = Number(flags["settle-ms"] ?? 800);

  const repoRoot = path.resolve(import.meta.dirname, "..");
  const outDir = path.join(repoRoot, "docs", "screenshots", label);
  await mkdir(outDir, { recursive: true });

  const existing = (await readdir(outDir)).filter((f) => f.endsWith(".png")).sort();
  const previous = existing.length > 0 ? path.join(outDir, existing[existing.length - 1]) : null;

  const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox"] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width, height });

    if (flags.email && flags.password) {
      const cookies = await loginCookies(base, flags.email, flags.password);
      const hostname = new URL(base).hostname;
      for (const raw of cookies) {
        const [pair] = raw.split(";");
        const separatorIndex = pair.indexOf("=");
        const name = pair.slice(0, separatorIndex);
        const value = pair.slice(separatorIndex + 1);
        await page.setCookie({ name, value, domain: hostname, path: "/" });
      }
    }

    // AppShell shows a one-time onboarding tour overlay on a section's first visit
    // (tracked per-section in localStorage). A snapshot should reflect the steady-state
    // screen, not that overlay, so mark both sections as already seen before navigating.
    await page.evaluateOnNewDocument(() => {
      for (const section of ["admin", "app"]) {
        window.localStorage.setItem(`hosthub:onboarding-seen:${section}`, "1");
      }
    });

    await page.goto(`${base}${routePath}`, { waitUntil: "networkidle0", timeout: 30000 });
    // Promise.withResolvers() would be preferred here, but it requires Node 22+ and this repo's
    // tooling targets Node 20 (see apps/web's own engines); executor form is the compatible option.
    await new Promise<void>((resolve) => setTimeout(resolve, settleMs));

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const outFile = path.join(outDir, `${timestamp}.png`);
    await page.screenshot({ path: outFile as `${string}.png`, fullPage });

    if (previous) console.log(`PREVIOUS: ${previous}`);
    console.log(outFile);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err instanceof Error ? err.message : err);
  process.exit(1);
});
