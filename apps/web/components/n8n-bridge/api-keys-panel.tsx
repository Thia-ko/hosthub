"use client";

import { useState } from "react";
import { Key, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { copyToClipboard } from "@/lib/utils";
import { useAsyncData } from "@/lib/use-async-data";
import type { ApiKey, ApiKeyCreated, ApiKeyScope } from "@/lib/types";

const SCOPE_LABEL: Record<ApiKeyScope, string> = {
  "prompt:read": "Ler o prompt ativo",
  "data:read": "Ler dados coletados pela IA",
  "messages:write": "Enviar mensagens no WhatsApp",
};

const ALL_SCOPES = Object.keys(SCOPE_LABEL) as ApiKeyScope[];

function KeyRow({ apiKey, onRevoke }: { apiKey: ApiKey; onRevoke: (id: string) => Promise<void> }) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-md border px-3 py-2 text-sm">
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="font-medium">{apiKey.name}</span>
          <code className="rounded bg-muted/40 px-1.5 py-0.5 text-xs text-muted-foreground">
            {apiKey.key_prefix}…
          </code>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {apiKey.scopes.map((scope) => (
            <Badge key={scope} variant="outline" className="text-xs">
              {SCOPE_LABEL[scope]}
            </Badge>
          ))}
          {!apiKey.active ? (
            <Badge variant="secondary" className="text-xs">
              Revogada
            </Badge>
          ) : null}
        </div>
        <span className="text-xs text-muted-foreground">
          {apiKey.last_used_at
            ? `Usada pela ultima vez em ${new Date(apiKey.last_used_at).toLocaleString("pt-BR")}`
            : "Ainda nao usada"}
        </span>
      </div>
      {apiKey.active ? (
        <ConfirmDialog
          trigger={
            <Button size="icon" variant="ghost" className="size-7 shrink-0">
              <Trash2 className="size-3.5" />
            </Button>
          }
          title="Revogar API key"
          description={`Revogar "${apiKey.name}"? Qualquer integracao usando essa chave para de funcionar imediatamente - nao pode ser desfeito.`}
          confirmLabel="Revogar"
          destructive
          onConfirm={() => onRevoke(apiKey.id)}
        />
      ) : null}
    </div>
  );
}

function CreatedKeyDialog({ created, onClose }: { created: ApiKeyCreated | null; onClose: () => void }) {
  const [copied, setCopied] = useState(false);

  async function copyKey() {
    if (!created || !(await copyToClipboard(created.key))) return;
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Dialog open={created !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>API key criada</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Copie agora - por seguranca, essa chave nao pode ser exibida novamente. Se perder, sera preciso criar uma
          nova.
        </p>
        <div className="flex items-center gap-2">
          <code className="min-w-0 flex-1 break-all rounded-md border bg-muted/40 px-3 py-1.5 text-xs">
            {created?.key}
          </code>
          <Button variant="outline" size="sm" onClick={copyKey}>
            {copied ? "Copiado" : "Copiar"}
          </Button>
        </div>
        <DialogFooter>
          <Button onClick={onClose}>Ja copiei, fechar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddKeyForm({ onAdd }: { onAdd: (name: string, scopes: ApiKeyScope[]) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<ApiKeyScope[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleScope(scope: ApiKeyScope) {
    setScopes((current) => (current.includes(scope) ? current.filter((item) => item !== scope) : [...current, scope]));
  }

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      await onAdd(name, scopes);
      setOpen(false);
      setName("");
      setScopes([]);
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)} className="w-fit">
        <Plus className="size-3.5" />
        Nova API key
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed p-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="api-key-name">Nome</Label>
        <Input
          id="api-key-name"
          placeholder="Ex: n8n producao, backend do cliente"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Permissoes</Label>
        {ALL_SCOPES.map((scope) => (
          <div key={scope} className="flex items-center gap-2">
            <Checkbox checked={scopes.includes(scope)} onCheckedChange={() => toggleScope(scope)} />
            <span className="text-sm">{SCOPE_LABEL[scope]}</span>
          </div>
        ))}
      </div>
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      <div className="flex gap-2">
        <Button size="sm" onClick={submit} disabled={saving || !name.trim() || scopes.length === 0}>
          {saving ? "Criando..." : "Criar"}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

export function ApiKeysPanel({ instanceId }: { instanceId: string }) {
  const {
    data: apiKeys,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<ApiKey[]>(`/instances/${instanceId}/api-keys`), [instanceId]);
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);

  async function addKey(name: string, scopes: ApiKeyScope[]) {
    const result = await apiFetch<ApiKeyCreated>(`/instances/${instanceId}/api-keys`, {
      method: "POST",
      body: JSON.stringify({ name, scopes }),
    });
    setCreated(result);
    reload();
  }

  async function revokeKey(id: string) {
    await apiFetch(`/instances/${instanceId}/api-keys/${id}`, { method: "DELETE" });
    reload();
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-medium">API keys</p>
        <p className="text-xs text-muted-foreground">
          Credenciais para um sistema externo (n8n, ou o backend de uma equipe de dev propria) chamar a API publica
          desta instancia sem precisar de um login. Cada chave so pode fazer o que suas permissoes autorizam.
        </p>
      </div>
      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && !error && apiKeys && apiKeys.length === 0 ? (
        <EmptyState title="Nenhuma API key criada ainda." icon={Key} />
      ) : null}
      {!loading && !error && apiKeys && apiKeys.length > 0 ? (
        <div className="flex flex-col gap-2">
          {apiKeys.map((apiKey) => (
            <KeyRow key={apiKey.id} apiKey={apiKey} onRevoke={revokeKey} />
          ))}
        </div>
      ) : null}
      <AddKeyForm onAdd={addKey} />
      <CreatedKeyDialog created={created} onClose={() => setCreated(null)} />
    </div>
  );
}
