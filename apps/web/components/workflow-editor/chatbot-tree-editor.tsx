"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { ChatbotNode } from "@/lib/types";

interface NodeFormData {
  label: string;
  keywords: string[];
  message: string;
}

function NodeForm({
  initialLabel = "",
  initialKeywords = "",
  initialMessage = "",
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initialLabel?: string;
  initialKeywords?: string;
  initialMessage?: string;
  submitLabel: string;
  onSubmit: (data: NodeFormData) => Promise<void>;
  onCancel: () => void;
}) {
  const [label, setLabel] = useState(initialLabel);
  const [keywords, setKeywords] = useState(initialKeywords);
  const [message, setMessage] = useState(initialMessage);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        label,
        keywords: keywords
          .split(",")
          .map((keyword) => keyword.trim())
          .filter(Boolean),
        message,
      });
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-dashed p-3">
      <div className="flex flex-col gap-1.5">
        <Label>Nome da opcao</Label>
        <Input value={label} onChange={(event) => setLabel(event.target.value)} placeholder="Ex: Vendas" />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Palavras-chave (separadas por virgula, opcional)</Label>
        <Input
          value={keywords}
          onChange={(event) => setKeywords(event.target.value)}
          placeholder="vendas, comprar, preco"
        />
        <p className="text-xs text-muted-foreground">
          O cliente tambem pode escolher digitando so o numero da opcao, na ordem mostrada.
        </p>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Mensagem enviada ao cliente</Label>
        <Textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={3} />
      </div>
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      <div className="flex gap-2">
        <Button size="sm" onClick={submit} disabled={saving || !label.trim() || !message.trim()}>
          {saving ? "Salvando..." : submitLabel}
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

function NodeCard({
  node,
  childrenByParent,
  depth,
  onAddChild,
  onUpdate,
  onDelete,
}: {
  node: ChatbotNode;
  childrenByParent: Map<string, ChatbotNode[]>;
  depth: number;
  onAddChild: (parentId: string, data: NodeFormData) => Promise<void>;
  onUpdate: (id: string, data: NodeFormData) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [addingChild, setAddingChild] = useState(false);
  const children = childrenByParent.get(node.id) ?? [];
  const indent = { marginLeft: depth * 20 };

  return (
    <div className="flex flex-col gap-2" style={indent}>
      <div className="rounded-md border p-3">
        {editing ? (
          <NodeForm
            initialLabel={node.label}
            initialKeywords={node.keywords.join(", ")}
            initialMessage={node.message}
            submitLabel="Salvar"
            onCancel={() => setEditing(false)}
            onSubmit={async (data) => {
              await onUpdate(node.id, data);
              setEditing(false);
            }}
          />
        ) : (
          <div className="flex items-start justify-between gap-2">
            <div className="flex flex-col gap-1.5">
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-sm font-medium">{node.label}</span>
                {node.keywords.map((keyword) => (
                  <Badge key={keyword} variant="outline" className="text-xs">
                    {keyword}
                  </Badge>
                ))}
              </div>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">{node.message}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                Editar
              </Button>
              <ConfirmDialog
                trigger={
                  <Button size="icon" variant="ghost" className="size-7 shrink-0">
                    <Trash2 className="size-3.5" />
                  </Button>
                }
                title="Remover opcao"
                description={
                  children.length > 0
                    ? `Remover "${node.label}" tambem remove as ${children.length} opcao(oes) dentro dela. Clientes parados aqui voltam ao menu principal na proxima mensagem.`
                    : `Remover "${node.label}"? Clientes parados aqui voltam ao menu principal na proxima mensagem.`
                }
                confirmLabel="Remover"
                destructive
                onConfirm={() => onDelete(node.id)}
              />
            </div>
          </div>
        )}
      </div>
      {!addingChild ? (
        <Button
          size="sm"
          variant="ghost"
          className="w-fit"
          style={{ marginLeft: (depth + 1) * 20 }}
          onClick={() => setAddingChild(true)}
        >
          <Plus className="size-3.5" />
          Adicionar opcao
        </Button>
      ) : (
        <div style={{ marginLeft: (depth + 1) * 20 }}>
          <NodeForm
            submitLabel="Adicionar"
            onCancel={() => setAddingChild(false)}
            onSubmit={async (data) => {
              await onAddChild(node.id, data);
              setAddingChild(false);
            }}
          />
        </div>
      )}
      {children.map((child) => (
        <NodeCard
          key={child.id}
          node={child}
          childrenByParent={childrenByParent}
          depth={depth + 1}
          onAddChild={onAddChild}
          onUpdate={onUpdate}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}

export function ChatbotTreeEditor({ instanceId }: { instanceId: string }) {
  const {
    data: nodes,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<ChatbotNode[]>(`/instances/${instanceId}/chatbot-nodes`), [instanceId]);
  const [creatingRoot, setCreatingRoot] = useState(false);

  async function createNode(parentId: string | null, data: NodeFormData) {
    await apiFetch(`/instances/${instanceId}/chatbot-nodes`, {
      method: "POST",
      body: JSON.stringify({ parent_id: parentId, ...data }),
    });
    reload();
  }

  async function updateNode(id: string, data: NodeFormData) {
    await apiFetch(`/instances/${instanceId}/chatbot-nodes/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
    reload();
  }

  async function deleteNode(id: string) {
    await apiFetch(`/instances/${instanceId}/chatbot-nodes/${id}`, { method: "DELETE" });
    reload();
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!nodes) return null;

  const root = nodes.find((node) => node.parent_id === null) ?? null;
  const childrenByParent = new Map<string, ChatbotNode[]>();
  for (const node of nodes) {
    if (node.parent_id === null) continue;
    const list = childrenByParent.get(node.parent_id) ?? [];
    list.push(node);
    childrenByParent.set(node.parent_id, list);
  }
  for (const list of childrenByParent.values()) {
    list.sort((a, b) => a.order_index - b.order_index);
  }

  if (!root) {
    return (
      <div className="flex flex-col gap-3">
        <EmptyState
          title="Nenhum menu configurado ainda."
          description="Um chatbot sem IA: o cliente digita um numero ou palavra-chave e recebe uma resposta pronta, sem gastar tokens de IA. Comece criando a saudacao inicial."
        />
        {!creatingRoot ? (
          <Button size="sm" onClick={() => setCreatingRoot(true)} className="w-fit">
            <Plus className="size-3.5" />
            Criar menu principal
          </Button>
        ) : (
          <NodeForm
            initialLabel="Menu principal"
            submitLabel="Criar"
            onCancel={() => setCreatingRoot(false)}
            onSubmit={async (data) => {
              await createNode(null, data);
              setCreatingRoot(false);
            }}
          />
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        O cliente digita <code className="text-xs">menu</code> a qualquer momento para voltar ao inicio, ou escolhe
        uma opcao pelo numero (1, 2, 3...) na ordem mostrada abaixo, ou por uma das palavras-chave configuradas.
      </p>
      <NodeCard
        node={root}
        childrenByParent={childrenByParent}
        depth={0}
        onAddChild={createNode}
        onUpdate={updateNode}
        onDelete={deleteNode}
      />
    </div>
  );
}
