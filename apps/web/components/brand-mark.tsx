import { cn } from "@/lib/utils";

/**
 * Hosthub glyph: a hosted unit (rounded square) wired to three connected instances.
 * Literal reading of the product ("host" + "hub"), monochrome via currentColor so it
 * adapts to any surface (sidebar, badge, favicon).
 */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className={className}>
      <rect x="8" y="8" width="8" height="8" rx="2.1" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M12 8V4.9M8.7 14.8 6 17.4M15.3 14.8l2.7 2.6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="12" cy="3.7" r="1.4" fill="currentColor" />
      <circle cx="4.9" cy="18.5" r="1.4" fill="currentColor" />
      <circle cx="19.1" cy="18.5" r="1.4" fill="currentColor" />
    </svg>
  );
}

export function BrandLockup({
  subtitle,
  subtitleClassName = "text-muted-foreground",
  size = "sm",
  className,
}: {
  subtitle?: string;
  subtitleClassName?: string;
  size?: "sm" | "lg";
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
        <BrandMark className={markSize} />
      </span>
      <div className="flex min-w-0 flex-col leading-tight">
        <span className={cn("truncate font-semibold tracking-tight", titleSize)}>Hosthub</span>
        {subtitle ? <span className={cn("truncate text-xs", subtitleClassName)}>{subtitle}</span> : null}
      </div>
    </div>
  );
}
