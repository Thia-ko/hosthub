"use client";

import Link from "next/link";
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts";
import { Bot, FileText, MessageSquare, Star } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Progress } from "@/components/ui/progress";
import { StatCard } from "@/components/stat-card";
import { Sparkline } from "@/components/sparkline";
import { ErrorState, LoadingState } from "@/components/state";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { AnalyticsOverview, DashboardSummary } from "@/lib/types";

const chartConfig = {
  count: {
    label: "Mensagens",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

export function InstanceDashboard({ instanceId, promptHref }: { instanceId: string; promptHref?: string }) {
  const {
    data: summary,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<DashboardSummary>(`/instances/${instanceId}/dashboard/summary`), [instanceId]);
  const { data: analytics } = useAsyncData(
    () => apiFetch<AnalyticsOverview>(`/instances/${instanceId}/analytics/overview`),
    [instanceId]
  );

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!summary) return null;

  const chartData = summary.messages_by_hour.map((entry) => ({
    hour: `${entry.hour.toString().padStart(2, "0")}h`,
    count: entry.count,
  }));

  const usagePercent =
    summary.ai_assist_daily_limit > 0
      ? Math.min(100, (summary.ai_assist_usage_today / summary.ai_assist_daily_limit) * 100)
      : 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Mensagens de clientes hoje" icon={MessageSquare} className="sm:col-span-2">
          <p className="text-2xl font-semibold">{summary.total_messages}</p>
          <Sparkline data={summary.messages_last_7_days.map((d) => ({ value: d.count }))} />
        </StatCard>
        <StatCard title="Versoes de prompt" icon={FileText}>
          <p className="text-2xl font-semibold">{summary.prompt_versions_count}</p>
        </StatCard>
        <StatCard title="Uso do assistente de IA hoje" icon={Bot} className="sm:col-span-2">
          <p className="text-sm">
            {summary.ai_assist_usage_today} / {summary.ai_assist_daily_limit} tokens
          </p>
          <Progress value={usagePercent} />
          <Sparkline data={summary.ai_tokens_last_7_days.map((d) => ({ value: d.count }))} />
        </StatCard>
        <StatCard title="Satisfacao dos clientes" icon={Star}>
          {summary.csat_response_count > 0 ? (
            <>
              <p className="text-2xl font-semibold">{summary.csat_average?.toFixed(1)} / 5</p>
              <p className="text-xs text-muted-foreground">
                {summary.csat_response_count} {summary.csat_response_count === 1 ? "avaliacao" : "avaliacoes"}
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Sem avaliacoes ainda</p>
          )}
        </StatCard>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mensagens de clientes por hora ({summary.date})</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartContainer config={chartConfig} className="h-64 w-full">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="fillCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-count)" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="var(--color-count)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="hour" tickLine={false} axisLine={false} interval={1} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Area
                dataKey="count"
                type="monotone"
                stroke="var(--color-count)"
                strokeWidth={2}
                fill="url(#fillCount)"
              />
            </AreaChart>
          </ChartContainer>
          <p className="mt-2 text-xs text-muted-foreground">
            Conta apenas mensagens reais de clientes (texto, audio e imagem reconhecidos) - ecos,
            atualizacoes de status e midia sem suporte de resposta nao entram na contagem.
          </p>
        </CardContent>
      </Card>
      {analytics ? (
        <Card>
          <CardHeader>
            <CardTitle>Base de conhecimento</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground">Conversas analisadas</p>
                <p className="text-xl font-semibold">{analytics.analyzed_conversations}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">FAQs</p>
                <p className="text-xl font-semibold">{analytics.total_faqs}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Dados extraidos</p>
                <p className="text-xl font-semibold">{analytics.total_extracted}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Padroes de atendimento</p>
                <p className="text-xl font-semibold">{analytics.total_patterns}</p>
              </div>
            </div>
            {analytics.pending_prompt ? (
              promptHref ? (
                <Link href={promptHref}>
                  <Badge variant="secondary" className="cursor-pointer">
                    Prompt gerado automaticamente aguardando aprovacao
                  </Badge>
                </Link>
              ) : (
                <Badge variant="secondary">Prompt gerado automaticamente aguardando aprovacao</Badge>
              )
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
