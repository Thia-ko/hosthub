import type { ReactNode } from "react";
import { AlertCircle, Inbox, Loader2, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { GENERIC_LOAD_ERROR_MESSAGE } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function LoadingState({ label = "Carregando...", className }: { label?: string; className?: string }) {
  return (
    <div className={cn("flex items-center gap-2 py-10 text-sm text-muted-foreground", className)}>
      <Loader2 className="size-4 animate-spin" />
      {label}
    </div>
  );
}

export function ErrorState({
  message = GENERIC_LOAD_ERROR_MESSAGE,
  onRetry,
  className,
}: {
  message?: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-6 text-sm text-destructive",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <AlertCircle className="size-4 shrink-0" />
        {message}
      </div>
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Tentar novamente
        </Button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon: Icon = Inbox,
  bordered = true,
  className,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: LucideIcon;
  bordered?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl px-6 py-12 text-center motion-safe:animate-[state-fade-in_0.35s_ease-out]",
        bordered && "border border-border/70 bg-muted/30",
        className
      )}
    >
      <div className="flex size-11 items-center justify-center rounded-full bg-primary/10 text-primary ring-1 ring-primary/15">
        <Icon className="size-5" />
      </div>
      <div className="flex flex-col gap-1.5">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {description ? <p className="max-w-sm text-sm text-muted-foreground">{description}</p> : null}
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}

export function FormStatus({ tone, children }: { tone: "success" | "error"; children: ReactNode }) {
  return <p className={cn("text-sm", tone === "error" ? "text-destructive" : "text-muted-foreground")}>{children}</p>;
}
