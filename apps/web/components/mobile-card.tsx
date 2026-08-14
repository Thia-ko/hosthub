import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/** Stacked card list shown below `sm`; pairs with a `<Table>` hidden below `sm`. */
export function MobileCardList({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex flex-col gap-3 sm:hidden", className)}>{children}</div>;
}

export function MobileCard({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex flex-col gap-2 rounded-lg border bg-card p-4", className)}>{children}</div>;
}

export function MobileCardRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  );
}
