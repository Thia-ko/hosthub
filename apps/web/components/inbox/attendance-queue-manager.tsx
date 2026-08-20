"use client";

import { useState } from "react";
import { toast } from "sonner";
import { ArrowDown, ArrowUp, ChevronRight, Plus, Radio, Star, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import { cn } from "@/lib/utils";
import type { AttendanceQueue, QueueBasePriority } from "@/lib/types";

const PRIORITY_LABEL: Record<QueueBasePriority, string> = { normal: "Normal", high: "Alta", urgent: "Urgente" };
const PRIORITY_OPTIONS: QueueBasePriority[] = ["normal", "high", "urgent"];

// A fixed swatch instead of a free color input - keeps every queue's Kanban accent readable in
// both light and dark mode without validating arbitrary hex contrast.
const COLOR_SWATCHES = ["#64748b", "#2563eb", "#059669", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2", "#db2777"];

function isQueueBasePriority(value: string): value is QueueBasePriority {
  return value === "normal" || value === "high" || value === "urgent";
}

function QueueRow({
  queue,
  isFirst,
  isLast,
  onUpdate,
  onDelete,
  onMove,
}: {
  queue: AttendanceQueue;
  isFirst: boolean;
  isLast: boolean;
  onUpdate: (id: string, patch: Partial<AttendanceQueue>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onMove: (id: string, direction: "up" | "down") => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [name, setName] = useState(queue.name);
  const [routingHint, setRoutingHint] = useState(queue.routing_hint ?? "");
  const [keywords, setKeywords] = useState(queue.keywords ?? "");

  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between gap-2 px-3 py-2.5">
        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          <ChevronRight
            className={cn("size-4 shrink-0 text-muted-foreground transition-transform", expanded && "rotate-90")}
          />
          <span className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: queue.color }} />
          <span className="truncate text-sm font-medium">{queue.name}</span>
          {queue.is_default ? (
            <Badge variant="secondary" className="shrink-0 gap-1">
              <Star className="size-3" /> Padrao
            </Badge>
          ) : null}
          <Badge variant="outline" className="shrink-0 text-[10px] font-normal">
            {PRIORITY_LABEL[queue.base_priority]}
          </Badge>
          {!queue.active ? (
            <Badge variant="outline" className="shrink-0 text-[10px] font-normal text-muted-foreground">
              Inativa
            </Badge>
          ) : null}
        </button>
        <div className="flex shrink-0 items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            disabled={isFirst}
            onClick={() => onMove(queue.id, "up")}
          >
            <ArrowUp className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            disabled={isLast}
            onClick={() => onMove(queue.id, "down")}
          >
            <ArrowDown className="size-4" />
          </Button>
          <ConfirmDialog
            trigger={
              <Button variant="ghost" size="icon" className="size-8 text-destructive" disabled={queue.is_default}>
                <Trash2 className="size-4" />
              </Button>
            }
            title={`Excluir fila "${queue.name}"?`}
            description="Atendimentos nesta fila sao movidos para a fila padrao. Esta acao nao pode ser desfeita."
            confirmLabel="Excluir"
            destructive
            onConfirm={() => onDelete(queue.id)}
          />
        </div>
      </div>

      {expanded ? (
        <div className="flex flex-col gap-3 border-t p-3">
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-muted-foreground">Nome da fila</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={() => name.trim() && name !== queue.name && onUpdate(queue.id, { name: name.trim() })}
              className="h-8 w-64"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs text-muted-foreground">
                Quando a IA deve encaminhar para esta fila (descricao livre para o modelo)
              </Label>
              <Textarea
                value={routingHint}
                onChange={(e) => setRoutingHint(e.target.value)}
                onBlur={() =>
                  routingHint !== (queue.routing_hint ?? "") && onUpdate(queue.id, { routing_hint: routingHint })
                }
                placeholder="Ex: duvidas sobre cobranca, reembolso, nota fiscal"
                className="min-h-16 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs text-muted-foreground">
                Palavras-chave (separadas por virgula, usadas quando o cliente pede humano direto)
              </Label>
              <Textarea
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                onBlur={() => keywords !== (queue.keywords ?? "") && onUpdate(queue.id, { keywords })}
                placeholder="Ex: reembolso, cobranca, nota fiscal"
                className="min-h-16 text-sm"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground">Prioridade da fila</Label>
              <Select
                value={queue.base_priority}
                onValueChange={(value) => {
                  if (isQueueBasePriority(value)) onUpdate(queue.id, { base_priority: value });
                }}
              >
                <SelectTrigger size="sm" className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITY_OPTIONS.map((priority) => (
                    <SelectItem key={priority} value={priority}>
                      {PRIORITY_LABEL[priority]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-1.5">
              <Label className="text-xs text-muted-foreground">Cor</Label>
              {COLOR_SWATCHES.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => onUpdate(queue.id, { color })}
                  className="size-5 rounded-full ring-offset-2 ring-offset-background transition-shadow"
                  style={{ backgroundColor: color, boxShadow: color === queue.color ? "0 0 0 2px var(--ring)" : undefined }}
                  aria-label={color}
                />
              ))}
            </div>

            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <Checkbox
                checked={queue.active}
                disabled={queue.is_default}
                onCheckedChange={(checked) => onUpdate(queue.id, { active: checked === true })}
              />
              Ativa
            </label>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function AddQueueForm({ onAdd }: { onAdd: (name: string) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  if (!open) {
    return (
      <Button variant="outline" size="sm" className="w-fit" onClick={() => setOpen(true)}>
        <Plus className="size-4" />
        Nova fila
      </Button>
    );
  }

  return (
    <form
      className="flex items-end gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!name.trim()) return;
        setSaving(true);
        onAdd(name.trim())
          .then(() => {
            setName("");
            setOpen(false);
          })
          .finally(() => setSaving(false));
      }}
    >
      <div className="flex flex-col gap-1.5">
        <Label className="text-xs text-muted-foreground">Nome da fila</Label>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex: Financeiro" autoFocus />
      </div>
      <Button type="submit" size="sm" disabled={saving || !name.trim()}>
        {saving ? "Criando..." : "Criar"}
      </Button>
      <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(false)}>
        Cancelar
      </Button>
    </form>
  );
}

export function AttendanceQueueManager({ instanceId }: { instanceId: string }) {
  const { data: queues, error, loading, reload } = useAsyncData(
    () => apiFetch<AttendanceQueue[]>(`/instances/${instanceId}/attendance-queues`),
    [instanceId]
  );

  async function handleCreate(name: string) {
    try {
      await apiFetch(`/instances/${instanceId}/attendance-queues`, {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      reload();
    } catch (err) {
      toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
      throw err;
    }
  }

  async function handleUpdate(id: string, patch: Partial<AttendanceQueue>) {
    try {
      await apiFetch(`/instances/${instanceId}/attendance-queues/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      reload();
    } catch (err) {
      toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    }
  }

  async function handleDelete(id: string) {
    await apiFetch(`/instances/${instanceId}/attendance-queues/${id}`, { method: "DELETE" });
    reload();
  }

  async function handleMove(id: string, direction: "up" | "down") {
    if (!queues) return;
    const index = queues.findIndex((q) => q.id === id);
    const swapWith = direction === "up" ? index - 1 : index + 1;
    if (index < 0 || swapWith < 0 || swapWith >= queues.length) return;
    const reordered = [...queues];
    [reordered[index], reordered[swapWith]] = [reordered[swapWith], reordered[index]];
    try {
      await apiFetch(`/instances/${instanceId}/attendance-queues/reorder`, {
        method: "PUT",
        body: JSON.stringify({ ordered_ids: reordered.map((q) => q.id) }),
      });
      reload();
    } catch (err) {
      toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!queues) return null;

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Filas nomeadas para organizar os atendimentos escalados por time/assunto. A IA usa a descricao de
        cada fila para decidir para onde encaminhar; o pedido explicito de um humano usa as palavras-chave.
      </p>
      {queues.length === 0 ? (
        <EmptyState title="Nenhuma fila configurada." icon={Radio} />
      ) : (
        <div className="flex flex-col gap-3">
          {queues.map((queue, index) => (
            <QueueRow
              key={queue.id}
              queue={queue}
              isFirst={index === 0}
              isLast={index === queues.length - 1}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
              onMove={handleMove}
            />
          ))}
        </div>
      )}
      <AddQueueForm onAdd={handleCreate} />
    </div>
  );
}
