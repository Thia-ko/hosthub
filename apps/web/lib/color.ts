function srgbChannelToLinear(channel: number): number {
  const normalized = channel / 255;
  return normalized <= 0.04045 ? normalized / 12.92 : Math.pow((normalized + 0.055) / 1.055, 2.4);
}

/**
 * Converts a #RRGGBB hex color to an "L C H" triplet for CSS oklch(),
 * matching the format shadcn's generated CSS variables already use
 * (e.g. "--primary: oklch(0.205 0 0);").
 */
export function hexToOklch(hex: string): string {
  const match = /^#([0-9a-fA-F]{6})$/.exec(hex);
  if (!match) return "0 0 0";

  const r = srgbChannelToLinear(parseInt(match[1].slice(0, 2), 16));
  const g = srgbChannelToLinear(parseInt(match[1].slice(2, 4), 16));
  const b = srgbChannelToLinear(parseInt(match[1].slice(4, 6), 16));

  const l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
  const m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
  const s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;

  const lRoot = Math.cbrt(l);
  const mRoot = Math.cbrt(m);
  const sRoot = Math.cbrt(s);

  const bigL = 0.2104542553 * lRoot + 0.793617785 * mRoot - 0.0040720468 * sRoot;
  const a = 1.9779984951 * lRoot - 2.428592205 * mRoot + 0.4505937099 * sRoot;
  const bLab = 0.0259040371 * lRoot + 0.7827717662 * mRoot - 0.808675766 * sRoot;

  const chroma = Math.sqrt(a * a + bLab * bLab);
  let hue = (Math.atan2(bLab, a) * 180) / Math.PI;
  if (hue < 0) hue += 360;

  return `${bigL.toFixed(4)} ${chroma.toFixed(4)} ${hue.toFixed(2)}`;
}
