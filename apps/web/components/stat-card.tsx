import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/** Shared headline-number typography, exported so cards with branching content (e.g. "sem
 * dados ainda" states) can match it without duplicating the class string. */
export const statValueClassName = "text-3xl font-semibold tracking-tight";

/** Stat/KPI card: subtle uppercase label + icon badge in the header, a heavyweight value front
 * and center, arbitrary supporting content (sparkline, progress, badges) below. */
export function StatCard({
  title,
  value,
  icon: Icon,
  children,
  className,
}: {
  title: string;
  value?: ReactNode;
  icon: LucideIcon;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("[--card-spacing:--spacing(5)]", className)}>
      <CardHeader>
        <CardTitle className="text-xs font-medium tracking-wide text-muted-foreground/80 uppercase">
          {title}
        </CardTitle>
        <CardAction>
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="size-4" />
          </div>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {value !== undefined ? <p className={statValueClassName}>{value}</p> : null}
        {children}
      </CardContent>
    </Card>
  );
}
