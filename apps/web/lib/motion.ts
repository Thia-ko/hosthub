/** Mirrors --ease-brand from app/globals.css (cubic-bezier(0.16, 1, 0.3, 1)).
 * Framer Motion can't consume CSS custom properties in `ease`, so the curve is
 * duplicated here as the single source for every motion-driven component -
 * keep in sync if the token changes. */
export const EASE_BRAND = [0.16, 1, 0.3, 1] as const;
