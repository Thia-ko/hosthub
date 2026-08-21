"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { LogOut, Menu, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { apiFetch } from "@/lib/api-client";
import { EASE_BRAND } from "@/lib/motion";
import { useIsClient } from "@/lib/use-is-client";
import type { CurrentUser } from "@/lib/user-context";

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}

/** Persistent top bar for the main content area (not the sidebar): a route-driven greeting on
 * the left, and the user's profile menu (name, theme toggle, logout) on the right. Replaces
 * the old sidebar footer/brand block - see AppShell. */
export function AppHeader({
  greeting,
  user,
  onMenuClick,
}: {
  greeting: string;
  user: CurrentUser;
  onMenuClick: () => void;
}) {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useIsClient();
  const isDark = mounted && resolvedTheme === "dark";

  async function handleLogout() {
    await apiFetch("/auth/logout", { method: "POST" }).catch(() => null);
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="flex items-center justify-between gap-4 border-b bg-background px-4 py-4 lg:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuClick} aria-label="Abrir menu">
          <Menu className="size-5" />
        </Button>
        <motion.h1
          key={greeting}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.32, ease: EASE_BRAND }}
          className="truncate text-lg font-semibold tracking-tight"
        >
          {greeting}
        </motion.h1>
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <motion.button
            type="button"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            transition={{ duration: 0.18, ease: EASE_BRAND }}
            className="flex items-center gap-2 rounded-full py-1 pr-3 pl-1 outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring/50"
          >
            <Avatar size="sm">
              <AvatarFallback>{initials(user.fullName)}</AvatarFallback>
            </Avatar>
            <span className="hidden text-sm font-medium sm:inline">{user.fullName}</span>
          </motion.button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56">
          <DropdownMenuLabel className="flex flex-col">
            <span className="truncate text-sm font-medium">{user.fullName}</span>
            <span className="truncate text-xs font-normal text-muted-foreground">{user.email}</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => mounted && setTheme(isDark ? "light" : "dark")}>
            {isDark ? <Sun /> : <Moon />}
            {isDark ? "Modo claro" : "Modo escuro"}
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem variant="destructive" onSelect={handleLogout}>
            <LogOut />
            Sair
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
