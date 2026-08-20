import { cn } from "@/lib/utils";

/**
 * Hosthub glyph: a hosted unit (rounded square) wired to three connected instances.
 * Literal reading of the product ("host" + "hub"), monochrome via currentColor so it
 * adapts to any surface (sidebar, badge, favicon).
 *
 * `active` turns it into the product's "AI is working" signal instead of a generic spinner:
 * each connection line gets a short dash that appears to travel outward (marching-ants via
 * `stroke-dashoffset`), the node it leads to pulses in step, and the center unit breathes
 * slowly - reads as a live signal, not decoration. Staggered per node/line via inline
 * `animationDelay` so the three don't pulse in unison. `motion-safe:` skips all of it under
 * `prefers-reduced-motion`, leaving the static mark. Keyframes live in app/globals.css
 * (`brand-pulse`, `brand-flow`, `brand-breathe`) since they're plain CSS, not Tailwind utilities.
 */
const LINES = [
  { d: "M12 8V4.9", delay: "0ms" },
  { d: "M8.7 14.8 6 17.4", delay: "260ms" },
  { d: "M15.3 14.8l2.7 2.6", delay: "520ms" },
] as const;

const NODES = [
  { cx: 12, cy: 3.7, delay: "0ms" },
  { cx: 4.9, cy: 18.5, delay: "260ms" },
  { cx: 19.1, cy: 18.5, delay: "520ms" },
] as const;

export function BrandMark({ className, active = false }: { className?: string; active?: boolean }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className={className}>
      <rect
        x="8"
        y="8"
        width="8"
        height="8"
        rx="2.1"
        stroke="currentColor"
        strokeWidth="1.6"
        className={active ? "motion-safe:animate-[brand-breathe_2.4s_ease-in-out_infinite]" : undefined}
      />
      {LINES.map((line) => (
        <path
          key={line.d}
          d={line.d}
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeDasharray={active ? "2 3" : undefined}
          className={active ? "motion-safe:animate-[brand-flow_1s_linear_infinite]" : undefined}
          style={active ? { animationDelay: line.delay } : undefined}
        />
      ))}
      {NODES.map((node) => (
        <circle
          key={`${node.cx}-${node.cy}`}
          cx={node.cx}
          cy={node.cy}
          r="1.4"
          fill="currentColor"
          className={active ? "motion-safe:animate-[brand-pulse_1.3s_ease-in-out_infinite]" : undefined}
          style={active ? { animationDelay: node.delay } : undefined}
        />
      ))}
    </svg>
  );
}

export function BrandLockup({
  subtitle,
  subtitleClassName = "text-muted-foreground",
  size = "sm",
  active = false,
  className,
}: {
  subtitle?: string;
  subtitleClassName?: string;
  size?: "sm" | "lg";
  active?: boolean;
  className?: string;
}) {
  const badgeSize = size === "lg" ? "size-10" : "size-8";
  const markSize = size === "lg" ? "size-5" : "size-4";
  const titleSize = size === "lg" ? "text-base" : "text-sm";

  return (
    <div className={cn("flex min-w-0 items-center gap-2", className)}>
      <span
        className={cn(
          "flex shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground",
          badgeSize
        )}
      >
        <BrandMark className={markSize} active={active} />
      </span>
      <div className="flex min-w-0 flex-col leading-tight">
        <span className={cn("truncate font-semibold tracking-tight", titleSize)}>Hosthub</span>
        {subtitle ? <span className={cn("truncate text-xs", subtitleClassName)}>{subtitle}</span> : null}
      </div>
    </div>
  );
}
