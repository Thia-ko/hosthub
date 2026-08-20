import type { ThemeSettings } from "@/lib/types";

const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://api:8000";

/** Fallback brand color used when the API is unreachable (e.g. icon route rendered before the
 * backend is up) — matches ThemeSetting's own DB default so it never looks out of place. */
export const FALLBACK_PRIMARY_COLOR = "#008757";

export async function getThemeSettings(): Promise<ThemeSettings | null> {
  try {
    const response = await fetch(`${INTERNAL_API_URL}/api/v1/theme`, { cache: "no-store" });
    if (!response.ok) return null;
    return (await response.json()) as ThemeSettings;
  } catch {
    return null;
  }
}
