"use client";

import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { useIsClient } from "@/lib/use-is-client";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useIsClient();

  if (!mounted) return null;

  return (
    <Button
      variant="ghost"
      size="sm"
      className={cn("gap-2", className)}
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      {resolvedTheme === "dark" ? "Modo claro" : "Modo escuro"}
    </Button>
  );
}
