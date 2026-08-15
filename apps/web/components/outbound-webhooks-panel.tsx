"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { OutboundWebhookEvent, OutboundWebhookSubscription } from "@/lib/types";

const EVENT_LABEL: Record<OutboundWebhookEvent, string> = {
  message_received: "Mensagem recebida",
  thread_escalated: "Conversa escalada para humano",
  prompt_pending: "Prompt gerado aguardando aprovacao",
};

const ALL_EVENTS = Object.keys(EVENT_LABEL) as OutboundWebhookEvent[];

function SubscriptionRow({
  subscription,
  onToggleActive,
  onDelete,
}: {
  subscription: OutboundWebhookSubscription;
  onToggleActive: (id: string, active: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-md border px-3 py-2 text-sm">
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <span className="truncate font-mono text-xs">{subscription.url}</span>
        <div className="flex flex-wrap items-center gap-1.5">
          {subscription.events.map((event) => (
            <Badge key={event} variant="outline" className="text-xs">
              {EVENT_LABEL[event]}
            </Badge>
          ))}
          {!subscription.active ? (
            <Badge variant="secondary" className="text-xs">
              Desativada
            </Badge>
          ) : null}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <Button
          size="sm"
          variant="outline"
          onClick={() => onToggleActive(subscription.id, !subscription.active)}
        >
          {subscription.active ? "Desativar" : "Ativar"}
        </Button>
        <ConfirmDialog
          trigger={
            <Button size="icon" variant="ghost" className="size-7 shrink-0">
              <Trash2 className="size-3.5" />
            </Button>
          }
          title="Remover integracao"
          description="Remover este endpoint de webhook de saida? Ele para de receber eventos imediatamente."
          confirmLabel="Remover"
          destructive
          onConfirm={() => onDelete(subscription.id)}
        />
      </div>
    </div>
  );
}

function AddSubscriptionForm({
  onAdd,
}: {
  onAdd: (url: string, events: OutboundWebhookEvent[]) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [events, setEvents] = useState<OutboundWebhookEvent[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleEvent(event: OutboundWebhookEvent) {
    setEvents((current) =>
      current.includes(event) ? current.filter((item) => item !== event) : [...current, event]
    );
  }

  async function submit() {
    if (!url.trim() || events.length === 0) return;
    setSaving(true);
    setError(null);
    try {
      await onAdd(url.trim(), events);
      setUrl("");
      setEvents([]);
      setOpen(false);
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <Button size="sm" variant="outline" className="w-fit" onClick={() => setOpen(true)}>
        <Plus className="size-3.5" /> Adicionar integracao
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed p-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="outboundUrl">URL de destino</Label>
        <Input
          id="outboundUrl"
          placeholder="https://sua-ferramenta.com/webhook"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Eventos</Label>
        {ALL_EVENTS.map((event) => (
          <div key={event} className="flex items-center gap-2">
            <Checkbox checked={events.includes(event)} onCheckedChange={() => toggleEvent(event)} />
            <span className="text-sm">{EVENT_LABEL[event]}</span>
          </div>
        ))}
      </div>
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      <div className="flex gap-2">
        <Button size="sm" onClick={submit} disabled={saving || !url.trim() || events.length === 0}>
          Salvar
        </Button>
        <Button size="sm" variant="outline" onClick={() => setOpen(false)} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

export function OutboundWebhooksPanel({ instanceId }: { instanceId: string }) {
  const {
    data: subscriptions,
    error,
    loading,
    reload,
  } = useAsyncData(
    () => apiFetch<OutboundWebhookSubscription[]>(`/instances/${instanceId}/outbound-webhooks`),
    [instanceId]
  );

  async function addSubscription(url: string, events: OutboundWebhookEvent[]) {
    await apiFetch(`/instances/${instanceId}/outbound-webhooks`, {
      method: "POST",
      body: JSON.stringify({ url, events }),
    });
    reload();
  }

  async function toggleActive(id: string, active: boolean) {
    await apiFetch(`/instances/${instanceId}/outbound-webhooks/${id}`, {
      method: "PUT",
      body: JSON.stringify({ active }),
    });
    reload();
  }

  async function deleteSubscription(id: string) {
    await apiFetch(`/instances/${instanceId}/outbound-webhooks/${id}`, { method: "DELETE" });
    reload();
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">Integracoes de saida</p>
        <p className="text-xs text-muted-foreground">
          Notifica um endpoint externo (n8n, Zapier, CRM) via POST em JSON quando um dos eventos abaixo
          acontece nesta instancia.
        </p>
      </div>
      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && !error && subscriptions && subscriptions.length === 0 ? (
        <EmptyState title="Nenhuma integracao configurada ainda." />
      ) : null}
      {!loading && !error && subscriptions && subscriptions.length > 0 ? (
        <div className="flex flex-col gap-2">
          {subscriptions.map((subscription) => (
            <SubscriptionRow
              key={subscription.id}
              subscription={subscription}
              onToggleActive={toggleActive}
              onDelete={deleteSubscription}
            />
          ))}
        </div>
      ) : null}
      <AddSubscriptionForm onAdd={addSubscription} />
    </div>
  );
}
