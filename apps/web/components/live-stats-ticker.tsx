"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { PublicPlatformStats } from "@/lib/types";

/** Animates from 0 to `value` once it arrives from the API - never shows a placeholder or fake
 * number mid-flight, just counts up to whatever the platform-wide aggregate actually is. */
function useCountUp(value: number | null, durationMs = 1200): number {
  const [display, setDisplay] = useState(0);
  const frameRef = useRef(0);

  useEffect(() => {
    if (value === null) return;
    const target = value;
    const start = performance.now();
    function tick(now: number) {
      const progress = Math.min(1, (now - start) / durationMs);
      const eased = 1 - (1 - progress) * (1 - progress); // ease-out quad
      setDisplay(Math.round(target * eased));
      if (progress < 1) frameRef.current = requestAnimationFrame(tick);
    }
    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [value, durationMs]);

  return display;
}

function StatItem({ value, suffix, label }: { value: number | null; suffix?: string; label: string }) {
  const display = useCountUp(value);
  return (
    <div className="flex flex-col items-center gap-1 px-6 text-center">
      <span className="text-2xl font-semibold tabular-nums sm:text-3xl">
        {value === null ? "—" : `${display}${suffix ?? ""}`}
      </span>
      <span className="max-w-[14rem] text-xs text-muted-foreground sm:text-sm">{label}</span>
    </div>
  );
}

/** Live-ish proof of the product actually running, in the same spot a generic testimonial
 * quote would go - real numbers pulled from the platform-wide aggregate
 * (GET /demo/stats, unauthenticated, no per-tenant breakdown), not marketing copy. Renders
 * nothing on error or before the first load resolves - no fake fallback figure. */
export function LiveStatsTicker() {
  const { data, error } = useAsyncData(() => apiFetch<PublicPlatformStats>("/demo/stats"), []);

  if (error || data === null) return null;

  return (
    <div className="border-y bg-muted/20 px-4 py-6 sm:px-8">
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-6 sm:flex-row sm:flex-wrap sm:justify-center sm:gap-0 sm:divide-x sm:divide-border">
        <StatItem
          value={data.ai_resolved_threads}
          label={`Atendimentos resolvidos pela IA nos últimos ${data.window_days} dias`}
        />
        <StatItem
          value={data.resolution_rate_pct}
          suffix="%"
          label="Taxa de resolução sem intervenção humana"
        />
        <StatItem value={data.estimated_hours_saved} label="Horas de equipe economizadas (estimado)" />
      </div>
    </div>
  );
}
