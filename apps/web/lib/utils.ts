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
