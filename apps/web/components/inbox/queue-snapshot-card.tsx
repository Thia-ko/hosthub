"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, Radio } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api-client";
import { formatWait } from "@/lib/utils";
import type { QueueItem, QueueStatus } from "@/lib/types";

const POLL_INTERVAL_MS = 5000;

const LANE_STATUSES: Extract<QueueStatus, "queued" | "in_progress" | "on_hold">[] = [
  "queued",
  "in_progress",
  "on_hold",
];

const STATUS_LABEL: Record<(typeof LANE_STATUSES)[number], string> = {
  queued: "Na fila",
  in_progress: "Em atendimento",
  on_hold: "Retidas",
};

/** Live "chamados na fila" snapshot for the dashboard home - polls the same GET
 * /instances/{id}/queue endpoint as <QueuePanel> and the nav badge (AppShell's
 * useQueueCount), so the number here always matches what a client sees clicking into
 * "Filas de Atendimento". Independent poll loop (not shared state) since this card can be
 * mounted without the queue screen ever being opened. */
export function QueueSnapshotCard({ instanceId, queueHref }: { instanceId: string; queueHref: string }) {
  const [items, setItems] = useState<QueueItem[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    function poll() {
      apiFetch<QueueItem[]>(`/instances/${instanceId}/queue`)
        .then((data) => {
          if (!cancelled) setItems(data);
        })
        .catch(() => {
          // A transient poll failure shouldn't blank out a card that's just a dashboard
          // shortcut to <QueuePanel>, which surfaces the real error if the user clicks through.
        });
    }
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [instanceId]);

  const total = items?.length ?? 0;
  const urgentCount = items?.filter((item) => item.sla_risk !== "ok").length ?? 0;
  const byStatus = items
    ? LANE_STATUSES.map((status) => ({
        status,
        count: items.filter((item) => item.queue_status === status).length,
      })).filter((entry) => entry.count > 0)
    : [];
  const oldestWaitSeconds = items && items.length > 0 ? Math.max(...items.map((item) => item.wait_time_seconds)) : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-60" />
            <span className="relative inline-flex size-2.5 rounded-full bg-primary" />
          </span>
          Fila de atendimento
        </CardTitle>
        <CardAction>
          <Link href={queueHref}>
            <Button variant="ghost" size="sm">
              Ver fila
              <ArrowRight className="size-3.5" />
            </Button>
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {items === null ? (
          <p className="text-sm text-muted-foreground">Carregando...</p>
        ) : total === 0 ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Radio className="size-4" />
            <p className="text-sm">Nenhum atendimento aguardando um humano agora.</p>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-baseline gap-2">
              <p className="text-2xl font-semibold">{total}</p>
              <p className="text-sm text-muted-foreground">
                {total === 1 ? "conversa aguardando" : "conversas aguardando"}
              </p>
              {urgentCount > 0 ? (
                <Badge variant="destructive" className="ml-auto">
                  <AlertTriangle className="size-3" />
                  {urgentCount} em risco de SLA
                </Badge>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {byStatus.map((entry) => (
                <Badge key={entry.status} variant="secondary">
                  {STATUS_LABEL[entry.status]}: {entry.count}
                </Badge>
              ))}
            </div>
            {oldestWaitSeconds !== null ? (
              <p className="text-xs text-muted-foreground">Espera mais antiga: {formatWait(oldestWaitSeconds)}</p>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}
