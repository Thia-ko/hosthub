"use client";

import { useMemo, useState, useSyncExternalStore, type ComponentType, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot,
  Cable,
  Database,
  FileText,
  History,
  LayoutDashboard,
  LayoutTemplate,
  LogOut,
  Megaphone,
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
import { OnboardingTour, type OnboardingStep } from "@/components/onboarding-tour";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { ThemeToggle } from "@/components/theme-toggle";
import { apiFetch } from "@/lib/api-client";
import { ONBOARDING_SEEN_PREFIX } from "@/lib/constants";
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
    { href: "/app/prompt", label: "Agente de IA", icon: MessageSquare },
    { href: "/app/conexao", label: "Conexao", icon: Cable },
    { href: "/app/prompt/templates", label: "Templates", icon: LayoutTemplate },
    { href: "/app/prompt/dados-coletados", label: "Dados coletados", icon: Database },
    { href: "/app/prompt/historico", label: "Historico", icon: History },
    { href: "/app/conversations", label: "Conversas", icon: MessagesSquare },
    { href: "/app/campaigns", label: "Campanhas", icon: Megaphone },
    { href: "/app/webhook", label: "Webhook", icon: Webhook },
    { href: "/app/equipe", label: "Equipe", icon: Users },
  ],
};

const SECTION_LABEL: Record<Section, string> = {
  admin: "Painel administrativo",
  app: "Painel do cliente",
};

/** One onboarding step per nav item, targeted via the `data-tour` attribute set on each link
 * below. Shown automatically the first time a user reaches a section (tracked in localStorage
 * per section, see `ONBOARDING_SEEN_PREFIX`) and replayable anytime via the "Tour guiado"
 * button in the sidebar footer. */
const TOUR_STEPS: Record<Section, OnboardingStep[]> = {
  admin: [
    {
      target: '[data-tour="/admin"]',
      title: "Visao geral",
      description: "Resumo de tudo que importa: instancias, prompts pendentes e conversas aguardando humano.",
    },
    {
      target: '[data-tour="/admin/instances"]',
      title: "Instancias",
      description: "Crie, configure e acompanhe as instancias de WhatsApp de cada cliente.",
    },
    {
      target: '[data-tour="/admin/templates"]',
      title: "Templates",
      description: "Modelos de prompt prontos para usar como ponto de partida em novas instancias.",
    },
    {
      target: '[data-tour="/admin/theme"]',
      title: "Tema",
      description: "Personalize as cores e a identidade visual do painel.",
    },
    {
      target: '[data-tour="/admin/ai-settings"]',
      title: "IA",
      description: "Configuracoes gerais de inteligencia artificial da plataforma.",
    },
  ],
  app: [
    {
      target: '[data-tour="/app"]',
      title: "Dashboard",
      description: "Visao geral da sua instancia: conversas, prompts pendentes e metricas.",
    },
    {
      target: '[data-tour="/app/prompt"]',
      title: "Agente de IA",
      description: "Configure a identidade, o tom e o conhecimento do seu agente de IA.",
    },
    {
      target: '[data-tour="/app/conexao"]',
      title: "Conexao",
      description: "Conecte o WhatsApp da instancia via WhatsBotMais, Evolution API ou API Oficial da Meta.",
    },
    {
      target: '[data-tour="/app/prompt/templates"]',
      title: "Templates",
      description: "Escolha um modelo pronto para comecar a configurar seu agente mais rapido.",
    },
    {
      target: '[data-tour="/app/prompt/dados-coletados"]',
      title: "Dados coletados",
      description: "Veja o que a IA aprendeu automaticamente com as conversas dos clientes.",
    },
    {
      target: '[data-tour="/app/prompt/historico"]',
      title: "Historico",
      description: "Consulte e compare versoes anteriores do prompt.",
    },
    {
      target: '[data-tour="/app/conversations"]',
      title: "Conversas",
      description: "Acompanhe as conversas do WhatsApp em tempo real.",
    },
    {
      target: '[data-tour="/app/campaigns"]',
      title: "Campanhas",
      description: "Envie mensagens em massa para os contatos da sua instancia.",
    },
    {
      target: '[data-tour="/app/webhook"]',
      title: "Webhook",
      description: "Integre eventos da plataforma com seus proprios sistemas.",
    },
    {
      target: '[data-tour="/app/equipe"]',
      title: "Equipe",
      description: "Gerencie quem tem acesso a esta instancia.",
    },
  ],
};

/** Longest matching nav href wins, so nested routes (e.g. /app/prompt/templates) don't
 * highlight their parent (/app/prompt) at the same time. */
function activeHref(pathname: string, items: NavItem[]): string | null {
  const matches = items.filter((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  matches.sort((a, b) => b.href.length - a.href.length);
  return matches[0]?.href ?? null;
}

function subscribeToTourDismissal(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
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
  const tourSteps = TOUR_STEPS[section];
  const [tourStep, setTourStep] = useState(0);
  const tourSeen = useSyncExternalStore(
    subscribeToTourDismissal,
    () => window.localStorage.getItem(`${ONBOARDING_SEEN_PREFIX}${section}`) !== null,
    () => true
  );
  const [tourDismissed, setTourDismissed] = useState(false);
  const tourActive = !tourSeen && !tourDismissed;

  function closeTour() {
    setTourDismissed(true);
    window.localStorage.setItem(`${ONBOARDING_SEEN_PREFIX}${section}`, "1");
  }

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
              data-tour={item.href}
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
      <aside className="hidden border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-[1px_0_4px_rgba(0,0,0,0.04)] lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col dark:shadow-none">
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

      {tourActive ? (
        <OnboardingTour
          steps={tourSteps}
          stepIndex={tourStep}
          onNext={() => setTourStep((s) => Math.min(tourSteps.length - 1, s + 1))}
          onPrev={() => setTourStep((s) => Math.max(0, s - 1))}
          onSkip={closeTour}
          onFinish={closeTour}
        />
      ) : null}
    </div>
  );
}
