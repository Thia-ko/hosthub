"use client";

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import type { InstanceStatus } from "@/lib/types";

const STATUS_LABEL: Record<InstanceStatus, string> = {
  active: "Ativa",
  paused: "Pausada",
  archived: "Arquivada",
};

const STATUS_VARIANT: Record<InstanceStatus, "default" | "secondary" | "outline"> = {
  active: "default",
  paused: "secondary",
  archived: "outline",
};

/** Mirrors --ease-brand from app/globals.css (cubic-bezier(0.16, 1, 0.3, 1)).
 * Framer Motion can't consume CSS custom properties in `ease`, so the curve
 * is duplicated here — keep both values in sync if the token changes. */
const EASE_BRAND = [0.16, 1, 0.3, 1] as const;

const badgeMotion: Variants = {
  initial: { opacity: 0, y: 4, scale: 0.96 },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.32, ease: EASE_BRAND },
  },
};

export function StatusBadge({ status }: { status: InstanceStatus }) {
  const isActive = status === "active";
  const reduceMotion = useReducedMotion();

  return (
    <Badge asChild variant={STATUS_VARIANT[status]}>
      <motion.span
        initial={reduceMotion ? false : "initial"}
        animate="animate"
        variants={badgeMotion}
        whileHover={
          reduceMotion ? undefined : { scale: 1.06, transition: { duration: 0.18, ease: EASE_BRAND } }
        }
        whileTap={reduceMotion ? undefined : { scale: 0.97 }}
      >
        {isActive && (
          <span className="relative mr-1 flex size-1.5" aria-hidden="true">
            {!reduceMotion && (
              <motion.span
                className="absolute inline-flex size-full rounded-full bg-primary-foreground"
                animate={{ scale: [1, 2.4], opacity: [0.6, 0] }}
                transition={{ duration: 1.6, ease: EASE_BRAND, repeat: Infinity }}
              />
            )}
            <span className="relative inline-flex size-1.5 rounded-full bg-primary-foreground" />
          </span>
        )}
        {STATUS_LABEL[status]}
      </motion.span>
    </Badge>
  );
}
