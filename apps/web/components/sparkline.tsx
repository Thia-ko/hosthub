"use client";

import { useId } from "react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

/** Compact trend line for a stat card - last N days at a glance, no axes/labels/tooltip (the
 * exact numbers already sit above it as the headline figure). Gradient id is per-instance
 * (useId) since multiple sparklines render on the same page and SVG ids are document-global. */
export function Sparkline({ data, className }: { data: { value: number }[]; className?: string }) {
  const gradientId = `sparkline-${useId()}`;
  const flat = data.every((point) => point.value === 0);

  return (
    <div className={className} aria-hidden="true">
      <ResponsiveContainer width="100%" height={32}>
        <AreaChart data={data} margin={{ top: 2, right: 1, bottom: 0, left: 1 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.35} />
              <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <Area
            dataKey="value"
            type="monotone"
            stroke="var(--primary)"
            strokeWidth={1.5}
            strokeOpacity={flat ? 0.3 : 1}
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
