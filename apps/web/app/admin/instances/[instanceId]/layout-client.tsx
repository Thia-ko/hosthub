"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ErrorState, LoadingState } from "@/components/state";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import { InstanceDetailProvider } from "@/lib/instance-detail-context";
import { cn } from "@/lib/utils";
import type { InstanceDetail } from "@/lib/types";
import { StatusBadge } from "../status-badge";

const TABS = [
  { href: "", label: "Geral" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/prompt", label: "Prompt" },
  { href: "/prompt/dados-coletados", label: "Dados coletados" },
  { href: "/prompt/historico", label: "Historico" },
  { href: "/conversations", label: "Conversas" },
  { href: "/webhook", label: "Webhook" },
];

export function InstanceDetailLayoutClient({ instanceId, children }: { instanceId: string; children: ReactNode }) {
  const pathname = usePathname();
  const {
    data: instance,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<InstanceDetail>(`/instances/${instanceId}`), [instanceId]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!instance) return null;

  const base = `/admin/instances/${instanceId}`;

  return (
    <InstanceDetailProvider instance={instance} reload={reload}>
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold">{instance.name}</h1>
          <StatusBadge status={instance.status} />
        </div>
        <div className="flex gap-1 border-b">
          {TABS.map((tab) => {
            const href = `${base}${tab.href}`;
            const active = pathname === href;
            return (
              <Link
                key={tab.href}
                href={href}
                className={cn(
                  "-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "border-primary text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )}
              >
                {tab.label}
              </Link>
            );
          })}
        </div>
        {children}
      </div>
    </InstanceDetailProvider>
  );
}
