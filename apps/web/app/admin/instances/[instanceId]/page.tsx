"use client";

import { useEffect, useState, use as usePromise } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { InstanceDetail, InstanceStatus } from "@/lib/types";

export default function AdminInstanceDetailPage({
  params,
}: {
  params: Promise<{ instanceId: string }>;
}) {
  const { instanceId } = usePromise(params);
  const [instance, setInstance] = useState<InstanceDetail | null>(null);
  const [name, setName] = useState("");
  const [status, setStatus] = useState<InstanceStatus>("active");
  const [tokenLimit, setTokenLimit] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<InstanceDetail>(`/instances/${instanceId}`).then((data) => {
      setInstance(data);
      setName(data.name);
      setStatus(data.status);
      setTokenLimit(data.ai_assist_daily_token_limit?.toString() ?? "");
    });
  }, [instanceId]);

  async function handleSave() {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await apiFetch<InstanceDetail>(`/instances/${instanceId}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          status,
          ai_assist_daily_token_limit: tokenLimit ? Number(tokenLimit) : null,
        }),
      });
      setInstance(updated);
      setMessage("Alteracoes salvas.");
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Nao foi possivel salvar");
    } finally {
      setSaving(false);
    }
  }

  if (!instance) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  return (
    <div className="flex max-w-lg flex-col gap-4">
      <h1 className="text-xl font-semibold">{instance.name}</h1>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="name">Nome</Label>
        <Input id="name" value={name} onChange={(event) => setName(event.target.value)} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Status</Label>
        <Select value={status} onValueChange={(value) => setStatus(value as InstanceStatus)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="active">Ativa</SelectItem>
            <SelectItem value="paused">Pausada</SelectItem>
            <SelectItem value="archived">Arquivada</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="tokenLimit">Limite diario do assistente de IA (tokens)</Label>
        <Input
          id="tokenLimit"
          type="number"
          placeholder="Usar padrao global"
          value={tokenLimit}
          onChange={(event) => setTokenLimit(event.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Cliente responsavel</Label>
        <p className="text-sm text-muted-foreground">{instance.owner_email}</p>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>URL do webhook</Label>
        <p className="break-all text-sm text-muted-foreground">/webhooks/{instance.webhook_token}</p>
        <Link
          className="w-fit text-sm text-muted-foreground hover:underline"
          href={`/admin/instances/${instance.id}/webhook`}
        >
          Ver eventos recebidos
        </Link>
      </div>
      {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
      <Button onClick={handleSave} disabled={saving} className="w-fit">
        {saving ? "Salvando..." : "Salvar alteracoes"}
      </Button>
    </div>
  );
}
