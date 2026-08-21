"use client";

import Link from "next/link";
import { Bot, FileText, MessageSquare, MessagesSquare, Server, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Sparkline } from "@/components/sparkline";
import { StatCard, statValueClassName } from "@/components/stat-card";
import { ErrorState, LoadingState } from "@/components/state";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { AdminDashboardOverview } from "@/lib/types";

export default function AdminHomeView() {
  const { data: overview, error, loading, reload } = useAsyncData(
    () => apiFetch<AdminDashboardOverview>("/dashboard/overview"),
    []
  );

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!overview) return null;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Visao geral da plataforma</h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <StatCard title="Instancias" icon={Server} value={overview.total_instances} className="sm:col-span-2">
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="outline">{overview.active_instances} ativas</Badge>
            <Badge variant="secondary">{overview.paused_instances} pausadas</Badge>
            <Badge variant="secondary">{overview.archived_instances} arquivadas</Badge>
          </div>
        </StatCard>
        <StatCard title="Prompts pendentes de aprovacao" icon={FileText} value={overview.pending_prompts} />
        <StatCard title="Conversas aguardando humano" icon={MessagesSquare} value={overview.escalated_threads} />
        <StatCard title="Resolvido pela IA" icon={Sparkles}>
          {overview.threads_with_activity > 0 ? (
            <>
              <p className={statValueClassName}>{overview.resolution_rate_pct}%</p>
              <p className="text-xs text-muted-foreground">
                {overview.ai_resolved_threads} de {overview.threads_with_activity} conversas sem humano
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Sem conversas no periodo</p>
          )}
        </StatCard>
        <StatCard
          title="Mensagens de clientes hoje"
          icon={MessageSquare}
          value={overview.messages_today}
          className="sm:col-span-2"
        >
          <Sparkline data={overview.messages_last_7_days.map((d) => ({ value: d.count }))} />
        </StatCard>
        <StatCard
          title="Tokens de IA consumidos hoje"
          icon={Bot}
          value={overview.ai_tokens_used_today.toLocaleString("pt-BR")}
          className="sm:col-span-2"
        >
          <Sparkline data={overview.ai_tokens_last_7_days.map((d) => ({ value: d.count }))} />
        </StatCard>
      </div>
      <Link href="/admin/instances" className="text-sm text-primary underline-offset-4 hover:underline w-fit">
        Ver todas as instancias
      </Link>
    </div>
  );
}
