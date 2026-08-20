import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * navigator.clipboard is only available in secure contexts (HTTPS or localhost) - on a plain
 * HTTP dev/staging origin (e.g. the docker-compose Caddy proxy, which has no TLS) it's simply
 * undefined, so calling .writeText() throws a TypeError and crashes whatever button triggered
 * it. Falls back to the legacy execCommand("copy") textarea trick, which still works over HTTP.
 * Resolves to whether the copy actually succeeded so callers can adjust their UI accordingly.
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  if (typeof navigator !== "undefined" && navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // fall through to the legacy fallback below
    }
  }
  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}

/**
 * crypto.randomUUID() is only available in secure contexts (HTTPS or localhost) - on a plain
 * HTTP dev/staging origin (e.g. the docker-compose Caddy proxy, which has no TLS) it's simply
 * undefined, so calling it throws a TypeError and crashes whatever mounted the component (e.g.
 * a chat widget generating its session id on first render). crypto.getRandomValues has no such
 * restriction, so it's used to build an equivalent UUID v4 by hand as the fallback.
 */
export function randomId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID && (typeof window === "undefined" || window.isSecureContext)) {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

/** Formats a wait/duration in seconds as a compact human string ("45s", "12min", "2h05") -
 * shared by the queue Kanban cards and the dashboard's live queue snapshot, both driven by
 * `QueueItem.wait_time_seconds`. */
export function formatWait(seconds: number): string {
  if (seconds < 60) return `${Math.max(0, Math.round(seconds))}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h${String(minutes % 60).padStart(2, "0")}`;
}
