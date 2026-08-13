"use client";

import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Progress } from "@/components/ui/progress";
import { apiFetch } from "@/lib/api-client";
import type { DashboardSummary } from "@/lib/types";

const chartConfig = {
  count: {
    label: "Eventos",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

export function InstanceDashboard({ instanceId }: { instanceId: string }) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    apiFetch<DashboardSummary>(`/instances/${instanceId}/dashboard/summary`).then(setSummary);
  }, [instanceId]);

  if (!summary) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  const chartData = summary.events_by_hour.map((entry) => ({
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
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Eventos hoje</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{summary.total_events}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">Versoes de prompt</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-semibold">{summary.prompt_versions_count}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Uso do assistente de IA hoje
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <p className="text-sm">
              {summary.ai_assist_usage_today} / {summary.ai_assist_daily_limit} tokens
            </p>
            <Progress value={usagePercent} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Atendimentos por hora ({summary.date})</CardTitle>
        </CardHeader>
        <CardContent>
          <ChartContainer config={chartConfig} className="h-64 w-full">
            <BarChart data={chartData}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="hour" tickLine={false} axisLine={false} interval={1} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="count" fill="var(--color-count)" radius={4} />
            </BarChart>
          </ChartContainer>
          <p className="mt-2 text-xs text-muted-foreground">
            Metricas baseadas nos eventos brutos recebidos via webhook; serao refinadas quando o formato de
            mensagens da integracao for definido.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
