"use client";

import { useMemo, useState, type ComponentType, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot,
  Database,
  FileText,
  History,
  LayoutDashboard,
  LayoutTemplate,
  LogOut,
  Menu,
  MessageSquare,
  MessagesSquare,
  Palette,
  Server,
  Users,
  Webhook,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { BrandLockup } from "@/components/brand-mark";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { ThemeToggle } from "@/components/theme-toggle";
import { apiFetch } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

type Section = "admin" | "app";

const NAV: Record<Section, NavItem[]> = {
  admin: [
    { href: "/admin", label: "Visao geral", icon: LayoutDashboard },
    { href: "/admin/instances", label: "Instancias", icon: Server },
    { href: "/admin/templates", label: "Templates", icon: FileText },
    { href: "/admin/theme", label: "Tema", icon: Palette },
    { href: "/admin/ai-settings", label: "IA", icon: Bot },
  ],
  app: [
    { href: "/app", label: "Dashboard", icon: LayoutDashboard },
    { href: "/app/prompt", label: "Prompt", icon: MessageSquare },
    { href: "/app/prompt/templates", label: "Templates", icon: LayoutTemplate },
    { href: "/app/prompt/dados-coletados", label: "Dados coletados", icon: Database },
    { href: "/app/prompt/historico", label: "Historico", icon: History },
    { href: "/app/conversations", label: "Conversas", icon: MessagesSquare },
    { href: "/app/webhook", label: "Webhook", icon: Webhook },
    { href: "/app/equipe", label: "Equipe", icon: Users },
  ],
};

const SECTION_LABEL: Record<Section, string> = {
  admin: "Painel administrativo",
  app: "Painel do cliente",
};

/** Longest matching nav href wins, so nested routes (e.g. /app/prompt/templates) don't
 * highlight their parent (/app/prompt) at the same time. */
function activeHref(pathname: string, items: NavItem[]): string | null {
  const matches = items.filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  matches.sort((a, b) => b.href.length - a.href.length);
  return matches[0]?.href ?? null;
}

export function AppShell({
  section,
  user,
  topBar,
  children,
}: {
  section: Section;
  user: { fullName: string; email: string; role: "admin" | "client" };
  topBar?: ReactNode;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const items = NAV[section];
  const active = useMemo(() => activeHref(pathname, items), [pathname, items]);

  async function handleLogout() {
    await apiFetch("/auth/logout", { method: "POST" }).catch(() => null);
    router.push("/login");
    router.refresh();
  }

  const sidebarBody = (
    <div className="flex h-full flex-col">
      <div className="px-4 py-4">
        <BrandLockup subtitle={SECTION_LABEL[section]} subtitleClassName="text-sidebar-foreground/60" />
      </div>
      <nav className="flex flex-1 flex-col gap-1 px-2">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.href === active;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              aria-current={isActive ? "page" : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
              )}
            >
              <Icon className="size-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="flex flex-col gap-2 border-t border-sidebar-border px-3 py-3">
        <div className="flex items-center justify-between gap-2 px-1">
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-medium">{user.fullName}</span>
            <span className="truncate text-xs text-sidebar-foreground/60">{user.email}</span>
          </div>
          <Badge variant="secondary" className="shrink-0">
            {user.role === "admin" ? "Admin" : "Cliente"}
          </Badge>
        </div>
        <ThemeToggle className="w-full justify-start" />
        <Button variant="ghost" size="sm" className="w-full justify-start gap-2" onClick={handleLogout}>
          <LogOut className="size-4" />
          Sair
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-muted/20 lg:flex">
      <aside className="hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        {sidebarBody}
      </aside>

      <div className="flex items-center gap-3 border-b bg-background px-4 py-3 lg:hidden">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Abrir menu">
              <Menu className="size-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 bg-sidebar p-0 text-sidebar-foreground">
            <SheetTitle className="sr-only">Menu de navegacao</SheetTitle>
            {sidebarBody}
          </SheetContent>
        </Sheet>
        <BrandLockup />
      </div>

      <div className="flex-1 lg:pl-64">
        {topBar}
        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}
