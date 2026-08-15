"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormStatus } from "@/components/state";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { ResetClientPasswordButton } from "@/components/reset-client-password-button";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useInstanceDetail } from "@/lib/instance-detail-context";
import type { InstanceDetail, InstanceStatus } from "@/lib/types";

const AUTO_GEN_INTERVAL_LABEL: Record<InstanceDetail["auto_gen_interval"], string> = {
  off: "Por quantidade de conversas analisadas",
  "1d": "Diariamente",
  "3d": "A cada 3 dias",
  "1w": "Semanalmente",
};

export default function AdminInstanceGeneralPage() {
  const { instance, reload } = useInstanceDetail();
  const [name, setName] = useState(instance.name);
  const [status, setStatus] = useState<InstanceStatus>(instance.status);
  const [tokenLimit, setTokenLimit] = useState(instance.ai_assist_daily_token_limit?.toString() ?? "");
  const [whatsappInstanceName, setWhatsappInstanceName] = useState(instance.whatsapp_instance_name ?? "");
  const [autoGeneratePrompt, setAutoGeneratePrompt] = useState(instance.auto_generate_prompt);
  const [autoGenThreshold, setAutoGenThreshold] = useState(instance.auto_gen_conversation_threshold.toString());
  const [autoGenInterval, setAutoGenInterval] = useState(instance.auto_gen_interval);
  const [syncedInstance, setSyncedInstance] = useState<InstanceDetail>(instance);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [confirmArchive, setConfirmArchive] = useState(false);

  if (instance !== syncedInstance) {
    setSyncedInstance(instance);
    setName(instance.name);
    setStatus(instance.status);
    setTokenLimit(instance.ai_assist_daily_token_limit?.toString() ?? "");
    setWhatsappInstanceName(instance.whatsapp_instance_name ?? "");
    setAutoGeneratePrompt(instance.auto_generate_prompt);
    setAutoGenThreshold(instance.auto_gen_conversation_threshold.toString());
    setAutoGenInterval(instance.auto_gen_interval);
  }

  async function handleSave() {
    setSaving(true);
    setSaveStatus(null);
    try {
      await apiFetch(`/instances/${instance.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name,
          status,
          ai_assist_daily_token_limit: tokenLimit ? Number(tokenLimit) : null,
          whatsapp_instance_name: whatsappInstanceName,
          auto_generate_prompt: autoGeneratePrompt,
          auto_gen_conversation_threshold: Number(autoGenThreshold) || 5,
          auto_gen_interval: autoGenInterval,
        }),
      });
      reload();
      setSaveStatus({ tone: "success", text: "Alteracoes salvas." });
      toast.success("Alteracoes salvas.");
    } catch (err) {
      setSaveStatus({ tone: "error", text: errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE) });
    } finally {
      setSaving(false);
    }
  }

  function handleSaveClick() {
    if (status === "archived" && instance.status !== "archived") {
      setConfirmArchive(true);
      return;
    }
    handleSave();
  }

  return (
    <div className="flex max-w-lg flex-col gap-4">
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
        <Label htmlFor="whatsappInstanceName">Resposta automatica via WhatsApp</Label>
        <Input
          id="whatsappInstanceName"
          placeholder="Sem WhatsApp conectado"
          value={whatsappInstanceName}
          onChange={(event) => setWhatsappInstanceName(event.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          WhatsBotMais (API oficial): a credencial ja vem em cada atendimento, preencha qualquer valor (ex:
          &quot;ativo&quot;) so para ligar a resposta automatica. Evolution API: preencha com o nome exato da
          instancia configurada la. Deixe em branco para so registrar os eventos sem responder.
        </p>
      </div>
      <div className="flex flex-col gap-2 rounded-md border p-3">
        <div className="flex items-center gap-2">
          <Checkbox
            id="autoGeneratePrompt"
            checked={autoGeneratePrompt}
            onCheckedChange={(checked) => setAutoGeneratePrompt(checked === true)}
          />
          <Label htmlFor="autoGeneratePrompt">Gerar prompts automaticamente a partir das conversas</Label>
        </div>
        <p className="text-xs text-muted-foreground">
          Cria uma versao de prompt pendente com base nos dados extraidos das conversas. Ela nunca entra em
          uso sozinha - alguem precisa aprova-la em Prompt &gt; editor.
        </p>
        {autoGeneratePrompt ? (
          <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:items-end">
            <div className="flex flex-1 flex-col gap-1.5">
              <Label>Gatilho</Label>
              <Select
                value={autoGenInterval}
                onValueChange={(value) => setAutoGenInterval(value as InstanceDetail["auto_gen_interval"])}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(AUTO_GEN_INTERVAL_LABEL).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {autoGenInterval === "off" ? (
              <div className="flex flex-1 flex-col gap-1.5">
                <Label htmlFor="autoGenThreshold">Conversas analisadas por geracao</Label>
                <Input
                  id="autoGenThreshold"
                  type="number"
                  min={1}
                  value={autoGenThreshold}
                  onChange={(event) => setAutoGenThreshold(event.target.value)}
                />
              </div>
            ) : null}
          </div>
        ) : null}
        {instance.last_auto_gen_at ? (
          <p className="text-xs text-muted-foreground">
            Ultima geracao automatica: {new Date(instance.last_auto_gen_at).toLocaleString("pt-BR")}
          </p>
        ) : null}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Cliente responsavel</Label>
        <p className="text-sm text-muted-foreground">{instance.owner_email}</p>
        <ResetClientPasswordButton instanceId={instance.id} clientEmail={instance.owner_email} />
      </div>
      {saveStatus ? <FormStatus tone={saveStatus.tone}>{saveStatus.text}</FormStatus> : null}
      <Button onClick={handleSaveClick} disabled={saving} className="w-fit">
        {saving ? "Salvando..." : "Salvar alteracoes"}
      </Button>
      <ConfirmDialog
        open={confirmArchive}
        onOpenChange={setConfirmArchive}
        title="Arquivar instancia"
        description={
          <>
            Arquivar <strong>{instance.name}</strong> pausa o agente de IA: ele para de responder aos clientes
            no WhatsApp imediatamente. Voce pode reativar depois trocando o status de volta.
          </>
        }
        confirmLabel="Arquivar"
        destructive
        onConfirm={handleSave}
      />
    </div>
  );
}
