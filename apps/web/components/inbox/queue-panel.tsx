"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Clock, MessagesSquare, Radio, UserCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { apiFetch, errorMessage, GENERIC_LOAD_ERROR_MESSAGE, GENERIC_SAVE_ERROR_MESSAGE } from "@/lib/api-client";
import { cn, formatWait } from "@/lib/utils";
import type {
  AgentAvailability,
  AgentProfile,
  AttendanceQueue,
  EscalationReason,
  QueueContext,
  QueueItem,
  QueuePriority,
  QueueSlaRisk,
  QueueStatus,
} from "@/lib/types";

const POLL_INTERVAL_MS = 5000;

// Kanban columns are the workflow stages, same for every fila - which named queue a card
// belongs to is a filter/badge on top (see the tab strip in QueuePanel), not a separate column,
// since a card's queue and its status are independent axes.
const LANES: { status: QueueStatus; title: string; description: string }[] = [
  { status: "queued", title: "Na fila", description: "Aguardando alguem assumir" },
  { status: "in_progress", title: "Em atendimento", description: "Alguem do time esta cuidando" },
  { status: "on_hold", title: "Retidas", description: "Aguardando resposta do cliente" },
];

// Drag-and-drop status transitions valid from -> to. Anything not listed here is rejected with
// a toast instead of silently doing nothing, so a stray drop doesn't look like a bug.
const VALID_DRAG_TRANSITIONS: Record<string, "claim" | "hold" | "unhold" | "resolve"> = {
  "queued->in_progress": "claim",
  "in_progress->on_hold": "hold",
  "on_hold->in_progress": "unhold",
  "in_progress->resolved": "resolve",
  "on_hold->resolved": "resolve",
};

const REASON_LABEL: Record<EscalationReason, string> = {
  customer_request: "Pedido do cliente",
  ai_uncertain: "IA insegura",
  ai_failure: "Falha na IA",
};

const PRIORITY_BADGE: Record<QueuePriority, "secondary" | "default" | "destructive"> = {
  normal: "secondary",
  high: "default",
  urgent: "destructive",
};

const PRIORITY_LABEL: Record<QueuePriority, string> = {
  normal: "Normal",
  high: "Alta",
  urgent: "Urgente",
};

// Visual-only ring: color and pulse speed escalate with wait time, same "live signal" language
// as <BrandMark active /> (brand-pulse keyframe) instead of a countdown/progress bar - there's
// no enforced SLA deadline behind this, see app.services.queue.compute_sla_risk on the backend.
const SLA_RING: Record<QueueSlaRisk, string> = {
  ok: "ring-1 ring-border",
  warning: "ring-2 ring-primary/50 motion-safe:animate-[brand-pulse_2.4s_ease-in-out_infinite]",
  critical: "ring-2 ring-destructive/60 motion-safe:animate-[brand-pulse_1.1s_ease-in-out_infinite]",
};

const AGENT_STATUS_LABEL: Record<AgentAvailability, string> = {
  online: "Online",
  busy: "Ocupado",
  away: "Ausente",
  offline: "Offline",
};

const AGENT_STATUS_DOT: Record<AgentAvailability, string> = {
  online: "bg-emerald-500",
  busy: "bg-amber-500",
  away: "bg-muted-foreground/50",
  offline: "bg-border",
};

const AGENT_STATUS_OPTIONS: AgentAvailability[] = ["online", "busy", "away", "offline"];

function isAgentAvailability(value: string): value is AgentAvailability {
  return value === "online" || value === "busy" || value === "away" || value === "offline";
}

function QueueCard({
  item,
  onOpen,
  draggable,
  onDragStart,
}: {
  item: QueueItem;
  onOpen: () => void;
  draggable: boolean;
  onDragStart: (event: React.DragEvent<HTMLButtonElement>) => void;
}) {
  return (
    <button
      type="button"
      draggable={draggable}
      onDragStart={onDragStart}
      onClick={onOpen}
      className={cn(
        "flex w-full cursor-grab flex-col gap-2 rounded-xl border bg-card p-3 text-left ring-offset-2 ring-offset-background transition-shadow hover:shadow-md active:cursor-grabbing",
        SLA_RING[item.sla_risk]
      )}
      style={item.queue ? { borderLeftColor: item.queue.color, borderLeftWidth: 3 } : undefined}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">{item.sender_number}</span>
        <Badge variant={PRIORITY_BADGE[item.priority]}>{PRIORITY_LABEL[item.priority]}</Badge>
      </div>
      <p className="line-clamp-2 text-sm text-muted-foreground">{item.last_message_preview || "(sem mensagens)"}</p>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Clock className="size-3" />
          {formatWait(item.wait_time_seconds)}
        </span>
        {item.queue ? (
          <span className="inline-flex items-center gap-1">
            <span className="size-2 rounded-full" style={{ backgroundColor: item.queue.color }} />
            {item.queue.name}
          </span>
        ) : null}
        {item.escalation_reason ? <Badge variant="outline">{REASON_LABEL[item.escalation_reason]}</Badge> : null}
        {item.assigned_agent ? (
          <span className="inline-flex items-center gap-1">
            <UserCheck className="size-3" />
            {item.assigned_agent.full_name}
          </span>
        ) : null}
      </div>
    </button>
  );
}

function QueueDetailSheet({
  instanceId,
  item,
  queues,
  conversationsHref,
  onClose,
  onMutated,
}: {
  instanceId: string;
  item: QueueItem;
  queues: AttendanceQueue[];
  conversationsHref: string;
  onClose: () => void;
  onMutated: (updated: QueueItem) => void;
}) {
  const [context, setContext] = useState<QueueContext | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiFetch<QueueContext>(`/instances/${instanceId}/queue/${item.sender_number}/context`)
      .then((data) => {
        if (!cancelled) setContext(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setContextError(errorMessage(err, GENERIC_LOAD_ERROR_MESSAGE));
      });
    return () => {
      cancelled = true;
    };
  }, [instanceId, item.sender_number]);

  const runAction = useCallback(
    (action: "claim" | "hold" | "unhold" | "resolve") => {
      setBusy(true);
      apiFetch<QueueItem>(`/instances/${instanceId}/queue/${item.sender_number}/${action}`, { method: "POST" })
        .then((updated) => {
          onMutated(updated);
          if (action === "resolve") onClose();
        })
        .catch((err: unknown) => toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE)))
        .finally(() => setBusy(false));
    },
    [instanceId, item.sender_number, onMutated, onClose]
  );

  const reassignQueue = useCallback(
    (queueId: string) => {
      setBusy(true);
      apiFetch<QueueItem>(`/instances/${instanceId}/queue/${item.sender_number}/reassign-queue`, {
        method: "POST",
        body: JSON.stringify({ queue_id: queueId }),
      })
        .then(onMutated)
        .catch((err: unknown) => toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE)))
        .finally(() => setBusy(false));
    },
    [instanceId, item.sender_number, onMutated]
  );

  return (
    <Sheet open onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="flex flex-col gap-4 overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{item.sender_number}</SheetTitle>
          <SheetDescription>
            {item.escalation_reason ? REASON_LABEL[item.escalation_reason] : "Atendimento"}
            {item.ai_confidence !== null ? ` - confianca da IA: ${item.ai_confidence}%` : ""}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-3 px-4">
          {queues.length > 1 ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">Fila</span>
              <Select value={item.queue?.id} onValueChange={reassignQueue}>
                <SelectTrigger size="sm" className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {queues.map((queue) => (
                    <SelectItem key={queue.id} value={queue.id}>
                      {queue.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}

          {contextError ? (
            <ErrorState message={contextError} className="py-4" />
          ) : context === null ? (
            <LoadingState label="Resumindo atendimento..." className="py-4" />
          ) : (
            <>
              {context.intent_summary ? (
                <div className="rounded-lg border bg-muted/40 p-3">
                  <p className="text-xs font-medium text-muted-foreground">O que o cliente quer</p>
                  <p className="text-sm">{context.intent_summary}</p>
                </div>
              ) : null}
              <div className="flex flex-col gap-2">
                <p className="text-xs font-medium text-muted-foreground">Ultimas mensagens</p>
                <div className="flex flex-col gap-1.5">
                  {context.recent_messages.slice(-4).map((message) => (
                    <div
                      key={message.id}
                      className={cn(
                        "rounded-md px-2.5 py-1.5 text-sm",
                        message.direction === "inbound" ? "bg-muted" : "bg-primary/10 text-right"
                      )}
                    >
                      {message.text}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="flex flex-wrap gap-2 pt-2">
            {item.queue_status === "queued" ? (
              <Button size="sm" disabled={busy} onClick={() => runAction("claim")}>
                Assumir
              </Button>
            ) : null}
            {item.queue_status === "in_progress" ? (
              <>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => runAction("hold")}>
                  Colocar em espera
                </Button>
                <Button size="sm" disabled={busy} onClick={() => runAction("resolve")}>
                  Marcar como resolvido
                </Button>
              </>
            ) : null}
            {item.queue_status === "on_hold" ? (
              <>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => runAction("unhold")}>
                  Retomar atendimento
                </Button>
                <Button size="sm" disabled={busy} onClick={() => runAction("resolve")}>
                  Marcar como resolvido
                </Button>
              </>
            ) : null}
            <Button size="sm" variant="ghost" asChild>
              <Link href={`${conversationsHref}?sender=${encodeURIComponent(item.sender_number)}`}>
                Abrir conversa e responder
              </Link>
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export function QueuePanel({ instanceId, conversationsHref }: { instanceId: string; conversationsHref: string }) {
  const [items, setItems] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [queues, setQueues] = useState<AttendanceQueue[]>([]);
  const [queueFilter, setQueueFilter] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentProfile[] | null>(null);
  const [myUserId, setMyUserId] = useState<string | null>(null);
  const [openSender, setOpenSender] = useState<string | null>(null);
  const [dragSender, setDragSender] = useState<string | null>(null);
  const [dragOverStatus, setDragOverStatus] = useState<string | null>(null);
  const knownSenders = useRef<Set<string> | null>(null);

  const loadQueue = useCallback(() => {
    apiFetch<QueueItem[]>(`/instances/${instanceId}/queue`)
      .then((data) => {
        if (knownSenders.current !== null) {
          for (const entry of data) {
            if (!knownSenders.current.has(entry.sender_number)) {
              toast.info(`Novo atendimento na fila: ${entry.sender_number}`);
            }
          }
        }
        knownSenders.current = new Set(data.map((entry) => entry.sender_number));
        setItems(data);
        setError(null);
      })
      .catch((err: unknown) => setError(errorMessage(err, GENERIC_LOAD_ERROR_MESSAGE)));
  }, [instanceId]);

  const loadQueues = useCallback(() => {
    apiFetch<AttendanceQueue[]>(`/instances/${instanceId}/attendance-queues`)
      .then((data) => setQueues(data.filter((q) => q.active)))
      .catch(() => undefined);
  }, [instanceId]);

  const loadAgents = useCallback(() => {
    apiFetch<AgentProfile[]>(`/instances/${instanceId}/queue/agents`)
      .then(setAgents)
      .catch(() => {
        /* the agent strip is a nice-to-have - a failed fetch here shouldn't block the queue */
      });
    apiFetch<{ id: string }>("/auth/me")
      .then((user) => setMyUserId(user.id))
      .catch(() => undefined);
  }, [instanceId]);

  useEffect(() => {
    loadQueue();
    loadQueues();
    loadAgents();
    const interval = setInterval(loadQueue, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [loadQueue, loadQueues, loadAgents]);

  const handleMutated = useCallback((updated: QueueItem) => {
    setItems((current) =>
      (current ?? [])
        .map((entry) => (entry.sender_number === updated.sender_number ? updated : entry))
        .filter((entry) => entry.queue_status !== "resolved")
    );
    setOpenSender((current) => (updated.queue_status === "resolved" ? null : current));
  }, []);

  const runDragAction = useCallback(
    (senderNumber: string, action: "claim" | "hold" | "unhold" | "resolve") => {
      apiFetch<QueueItem>(`/instances/${instanceId}/queue/${senderNumber}/${action}`, { method: "POST" })
        .then(handleMutated)
        .catch((err: unknown) => toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE)));
    },
    [instanceId, handleMutated]
  );

  const myStatus = agents?.find((agent) => agent.user_id === myUserId)?.status ?? "offline";

  const setMyStatus = useCallback(
    (status: AgentAvailability) => {
      apiFetch<AgentProfile>(`/instances/${instanceId}/queue/agents/me`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      })
        .then(() => loadAgents())
        .catch((err: unknown) => toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE)));
    },
    [instanceId, loadAgents]
  );

  if (error) return <ErrorState message={error} onRetry={loadQueue} />;
  if (items === null) return <LoadingState />;

  const openItem = items.find((entry) => entry.sender_number === openSender) ?? null;
  const visibleItems = queueFilter ? items.filter((item) => item.queue?.id === queueFilter) : items;

  function handleDrop(targetStatus: string) {
    setDragOverStatus(null);
    if (!dragSender) return;
    const item = items?.find((entry) => entry.sender_number === dragSender);
    setDragSender(null);
    if (!item || item.queue_status === targetStatus) return;
    const action = VALID_DRAG_TRANSITIONS[`${item.queue_status}->${targetStatus}`];
    if (!action) {
      toast.error("Essa transicao nao e permitida - abra o card para ver as acoes disponiveis.");
      return;
    }
    runDragAction(item.sender_number, action);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Radio className="size-4" />
          Meu status na fila
        </div>
        <div className="flex items-center gap-3">
          <Select value={myStatus} onValueChange={(value) => { if (isAgentAvailability(value)) setMyStatus(value); }}>
            <SelectTrigger size="sm" className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {AGENT_STATUS_OPTIONS.map((status) => (
                <SelectItem key={status} value={status}>
                  {AGENT_STATUS_LABEL[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {agents ? (
            <div className="flex items-center gap-1.5">
              {agents.map((agent) => (
                <span
                  key={agent.user_id}
                  title={`${agent.full_name}: ${AGENT_STATUS_LABEL[agent.status]}`}
                  className={cn("size-2.5 rounded-full", AGENT_STATUS_DOT[agent.status])}
                />
              ))}
            </div>
          ) : null}
        </div>
      </div>

      {queues.length > 1 ? (
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setQueueFilter(null)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              queueFilter === null ? "border-foreground bg-foreground text-background" : "text-muted-foreground hover:text-foreground"
            )}
          >
            Todas
          </button>
          {queues.map((queue) => (
            <button
              key={queue.id}
              type="button"
              onClick={() => setQueueFilter(queue.id)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                queueFilter === queue.id ? "border-foreground text-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <span className="size-2 rounded-full" style={{ backgroundColor: queue.color }} />
              {queue.name}
            </button>
          ))}
        </div>
      ) : null}

      {items.length === 0 ? (
        <EmptyState
          title="Fila vazia."
          description="Quando a IA escalar um atendimento ou o cliente pedir um humano, ele aparece aqui."
          icon={MessagesSquare}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-4">
          {LANES.map((lane) => {
            const laneItems = visibleItems.filter((entry) => entry.queue_status === lane.status);
            return (
              <div
                key={lane.status}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOverStatus(lane.status);
                }}
                onDragLeave={() => setDragOverStatus((current) => (current === lane.status ? null : current))}
                onDrop={(e) => {
                  e.preventDefault();
                  handleDrop(lane.status);
                }}
                className={cn(
                  "flex flex-col gap-2 rounded-lg p-1 transition-colors",
                  dragOverStatus === lane.status && "bg-muted/60"
                )}
              >
                <div>
                  <h2 className="text-sm font-semibold">
                    {lane.title} <span className="text-muted-foreground">({laneItems.length})</span>
                  </h2>
                  <p className="text-xs text-muted-foreground">{lane.description}</p>
                </div>
                <div className="flex flex-col gap-2">
                  {laneItems.map((item) => (
                    <QueueCard
                      key={item.sender_number}
                      item={item}
                      onOpen={() => setOpenSender(item.sender_number)}
                      draggable
                      onDragStart={() => setDragSender(item.sender_number)}
                    />
                  ))}
                  {laneItems.length === 0 ? (
                    <p className="rounded-lg border border-dashed p-3 text-center text-xs text-muted-foreground">
                      Nada por aqui
                    </p>
                  ) : null}
                </div>
              </div>
            );
          })}

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOverStatus("resolved");
            }}
            onDragLeave={() => setDragOverStatus((current) => (current === "resolved" ? null : current))}
            onDrop={(e) => {
              e.preventDefault();
              handleDrop("resolved");
            }}
            className={cn(
              "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-4 text-center transition-colors",
              dragOverStatus === "resolved" ? "border-primary bg-primary/5" : "border-border"
            )}
          >
            <h2 className="text-sm font-semibold text-muted-foreground">Resolver</h2>
            <p className="text-xs text-muted-foreground">Arraste um card em atendimento ou em espera para ca</p>
          </div>
        </div>
      )}

      {openItem ? (
        <QueueDetailSheet
          instanceId={instanceId}
          item={openItem}
          queues={queues}
          conversationsHref={conversationsHref}
          onClose={() => setOpenSender(null)}
          onMutated={handleMutated}
        />
      ) : null}
    </div>
  );
}
