"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { Campaign, CampaignStatus } from "@/lib/types";

const STATUS_LABEL: Record<CampaignStatus, string> = {
  sending: "Enviando",
  completed: "Concluida",
  failed: "Falhou",
};

function CampaignRow({ campaign }: { campaign: Campaign }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{campaign.name}</CardTitle>
          <Badge variant={campaign.status === "failed" ? "destructive" : "secondary"}>
            {STATUS_LABEL[campaign.status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">{campaign.message}</p>
        <div className="flex flex-wrap gap-1.5 text-xs">
          <Badge variant="outline">{campaign.total_recipients} destinatarios</Badge>
          <Badge variant="outline">{campaign.sent_count} enviados</Badge>
          <Badge variant="outline">{campaign.skipped_count} fora da janela de 24h</Badge>
          {campaign.failed_count > 0 ? <Badge variant="destructive">{campaign.failed_count} falharam</Badge> : null}
        </div>
        <p className="text-xs text-muted-foreground">{new Date(campaign.created_at).toLocaleString("pt-BR")}</p>
      </CardContent>
    </Card>
  );
}

export function CampaignsPanel({ instanceId }: { instanceId: string }) {
  const { data: campaigns, error, loading, reload } = useAsyncData(
    () => apiFetch<Campaign[]>(`/instances/${instanceId}/campaigns`),
    [instanceId]
  );
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim() || !message.trim()) return;
    setSending(true);
    setSendError(null);
    try {
      await apiFetch(`/instances/${instanceId}/campaigns`, {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), message: message.trim() }),
      });
      setName("");
      setMessage("");
      reload();
    } catch (err) {
      setSendError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Nova campanha</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-xs text-muted-foreground">
            Envia para todo cliente que ja mandou mensagem para esta instancia - clientes sem mensagem nas
            ultimas 24h sao pulados automaticamente (WhatsApp exige template aprovado fora dessa janela, o
            HostHub ainda nao suporta).
          </p>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="campaignName">Nome da campanha</Label>
            <Input id="campaignName" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="campaignMessage">Mensagem</Label>
            <Textarea
              id="campaignMessage"
              className="min-h-24"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
          </div>
          {sendError ? <FormStatus tone="error">{sendError}</FormStatus> : null}
          <Button onClick={submit} disabled={sending || !name.trim() || !message.trim()} className="w-fit">
            {sending ? "Enviando..." : "Enviar campanha"}
          </Button>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Historico</p>
        <Button variant="outline" size="sm" onClick={reload}>
          Atualizar
        </Button>
      </div>
      {loading && !campaigns ? <LoadingState /> : null}
      {!campaigns && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {campaigns && campaigns.length === 0 ? <EmptyState title="Nenhuma campanha enviada ainda." /> : null}
      {campaigns && campaigns.length > 0 ? (
        <div className="flex flex-col gap-3">
          {campaigns.map((campaign) => (
            <CampaignRow key={campaign.id} campaign={campaign} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
