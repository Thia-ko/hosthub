"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Instancias</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <p className="text-2xl font-semibold">{overview.total_instances}</p>
            <div className="flex flex-wrap gap-1.5">
              <Badge variant="outline">{overview.active_instances} ativas</Badge>
              <Badge variant="secondary">{overview.paused_instances} pausadas</Badge>
              <Badge variant="secondary">{overview.archived_instances} arquivadas</Badge>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Prompts pendentes de aprovacao
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{overview.pending_prompts}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Conversas aguardando humano
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{overview.escalated_threads}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Mensagens de clientes hoje</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{overview.messages_today}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Tokens de IA consumidos hoje
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{overview.ai_tokens_used_today.toLocaleString("pt-BR")}</p>
          </CardContent>
        </Card>
      </div>
      <Link href="/admin/instances" className="text-sm text-primary underline-offset-4 hover:underline w-fit">
        Ver todas as instancias
      </Link>
    </div>
  );
}
