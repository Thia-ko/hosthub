"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Server } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import { useOwnInstances } from "@/lib/instance-context";
import { copyToClipboard } from "@/lib/utils";
import type {
  EvolutionQr,
  EvolutionStatus,
  InstanceDetail,
  MetaConnectResult,
  WhatsAppConnection,
  WhatsAppProvider,
} from "@/lib/types";

const PROVIDER_INFO: Record<WhatsAppProvider, { label: string; description: string }> = {
  whatsbotmais: {
    label: "WhatsBotMais",
    description: "Canal padrao, gerenciado no painel WhatsBotMais - sem necessidade de credenciais aqui.",
  },
  evolution: {
    label: "Evolution API",
    description: "Conecte via QR code usando sua propria instancia self-hosted da Evolution API.",
  },
  meta_cloud: {
    label: "API Oficial (Meta)",
    description: "Conecte diretamente com a API oficial do WhatsApp Business da Meta, usando Phone Number ID e Access Token.",
  },
};

function WhatsBotMaisPanel({ webhookUrl }: { webhookUrl: string }) {
  const [copied, setCopied] = useState(false);

  async function copyUrl() {
    if (!(await copyToClipboard(webhookUrl))) return;
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-col gap-3 text-sm">
      <p className="text-muted-foreground">
        Nenhuma credencial e necessaria aqui: o token de resposta chega automaticamente a cada mensagem recebida
        pelo webhook, e o numero de WhatsApp e conectado e gerenciado inteiramente no painel do WhatsBotMais.
      </p>
      <div className="flex flex-col gap-1.5">
        <Label>URL do webhook desta instancia</Label>
        <div className="flex items-center gap-2">
          <code className="break-all rounded-md border bg-muted/40 px-3 py-1.5 text-xs">{webhookUrl}</code>
          <Button variant="outline" size="sm" onClick={copyUrl}>
            {copied ? "Copiado" : "Copiar"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function QrDisplay({ qr }: { qr: EvolutionQr }) {
  if (qr.base64) {
    const src = qr.base64.startsWith("data:") ? qr.base64 : `data:image/png;base64,${qr.base64}`;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt="QR code para conectar o WhatsApp" className="size-56 rounded-md border" />;
  }
  if (qr.code) {
    return <code className="block break-all rounded-md border bg-muted/40 px-3 py-1.5 text-xs">{qr.code}</code>;
  }
  return <p className="text-sm text-muted-foreground">QR code nao disponivel no momento.</p>;
}

function EvolutionPanel({
  instanceId,
  connection,
  onChanged,
}: {
  instanceId: string;
  connection: WhatsAppConnection;
  onChanged: () => void;
}) {
  const alreadyConnected = connection.provider === "evolution" && !!connection.whatsapp_instance_name;
  const [instanceName, setInstanceName] = useState(connection.whatsapp_instance_name ?? "");
  const [qr, setQr] = useState<EvolutionQr | null>(null);
  const [state, setState] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!alreadyConnected) return;
    let cancelled = false;
    apiFetch<EvolutionQr>(`/instances/${instanceId}/whatsapp-connection/evolution/qr`)
      .then((result) => {
        if (cancelled) return;
        setQr(result);
        setState(result.state);
      })
      .catch(() => {
        // Best-effort: instance may already be fully connected server-side even if the QR
        // endpoint fails transiently - status polling below still reflects the real state.
      });
    return () => {
      cancelled = true;
    };
  }, [alreadyConnected, instanceId]);

  useEffect(() => {
    if (!qr || state === "open") return;
    const interval = setInterval(async () => {
      try {
        const result = await apiFetch<EvolutionStatus>(`/instances/${instanceId}/whatsapp-connection/evolution/status`);
        setState(result.state);
        if (result.state === "open") {
          toast.success("WhatsApp conectado via Evolution API.");
          onChanged();
        }
      } catch {
        // transient error - keep polling
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [qr, state, instanceId, onChanged]);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const result = await apiFetch<EvolutionQr>(`/instances/${instanceId}/whatsapp-connection/evolution/instance`, {
        method: "POST",
        body: JSON.stringify({ instance_name: instanceName }),
      });
      setQr(result);
      setState(result.state);
      toast.success("Instancia Evolution criada. Escaneie o QR code para conectar.");
      onChanged();
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
      toast.error("Nao foi possivel criar a instancia na Evolution API.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    try {
      await apiFetch(`/instances/${instanceId}/whatsapp-connection/evolution/instance`, { method: "DELETE" });
      toast.success("Instancia Evolution desconectada.");
      setQr(null);
      setState(null);
      onChanged();
    } catch (err) {
      toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setDisconnecting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {alreadyConnected ? (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Instancia:</span>
          <code className="text-xs">{connection.whatsapp_instance_name}</code>
          <Badge variant={state === "open" ? "default" : "secondary"}>
            {state === "open" ? "Conectado" : "Aguardando leitura do QR"}
          </Badge>
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="evolutionInstanceName">Nome da instancia</Label>
          <Input
            id="evolutionInstanceName"
            value={instanceName}
            onChange={(event) => setInstanceName(event.target.value)}
            placeholder="ex: cliente-nome"
          />
        </div>
      )}
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      {!alreadyConnected ? (
        <Button onClick={handleCreate} disabled={creating || !instanceName.trim()} className="w-fit">
          {creating ? "Criando..." : "Criar Instancia"}
        </Button>
      ) : null}
      {qr && state !== "open" ? (
        <div className="flex flex-col items-start gap-2">
          {!alreadyConnected ? (
            <Badge variant="secondary">Aguardando leitura do QR</Badge>
          ) : null}
          <QrDisplay qr={qr} />
        </div>
      ) : null}
      {alreadyConnected ? (
        <Button variant="destructive" size="sm" className="w-fit" onClick={handleDisconnect} disabled={disconnecting}>
          {disconnecting ? "Desconectando..." : "Desconectar"}
        </Button>
      ) : null}
    </div>
  );
}

function MetaPanel({
  instanceId,
  connection,
  onChanged,
}: {
  instanceId: string;
  connection: WhatsAppConnection;
  onChanged: () => void;
}) {
  const connected = connection.provider === "meta_cloud";
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [testing, setTesting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [result, setResult] = useState<MetaConnectResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleTest() {
    setTesting(true);
    setError(null);
    try {
      const res = await apiFetch<MetaConnectResult>(`/instances/${instanceId}/whatsapp-connection/meta/test`, {
        method: "POST",
        body: JSON.stringify({ phone_number_id: phoneNumberId, access_token: accessToken }),
      });
      setResult(res);
      toast.success("WhatsApp conectado via API Oficial (Meta).");
      onChanged();
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
      toast.error("Nao foi possivel conectar com a API Oficial (Meta).");
    } finally {
      setTesting(false);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    try {
      await apiFetch(`/instances/${instanceId}/whatsapp-connection/meta/instance`, { method: "DELETE" });
      toast.success("Conexao com a API Oficial (Meta) removida.");
      setResult(null);
      onChanged();
    } catch (err) {
      toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setDisconnecting(false);
    }
  }

  if (connected && !result) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-sm">
          Phone Number ID conectado: <code className="text-xs">{connection.meta_phone_number_id}</code>
        </p>
        <Button variant="destructive" size="sm" className="w-fit" onClick={handleDisconnect} disabled={disconnecting}>
          {disconnecting ? "Desconectando..." : "Desconectar"}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="metaPhoneNumberId">Phone Number ID</Label>
        <Input id="metaPhoneNumberId" value={phoneNumberId} onChange={(event) => setPhoneNumberId(event.target.value)} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="metaAccessToken">Access Token</Label>
        <Input
          id="metaAccessToken"
          type="password"
          value={accessToken}
          onChange={(event) => setAccessToken(event.target.value)}
        />
      </div>
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      {result ? (
        <FormStatus tone="success">
          Conectado: {result.display_phone_number} ({result.verified_name})
        </FormStatus>
      ) : null}
      <Button onClick={handleTest} disabled={testing || !phoneNumberId.trim() || !accessToken.trim()} className="w-fit">
        {testing ? "Testando..." : "Testar e conectar"}
      </Button>
    </div>
  );
}

export function WhatsAppConnectionView({ instanceId }: { instanceId: string }) {
  const {
    data: connection,
    error: connectionError,
    loading: connectionLoading,
    reload: reloadConnection,
  } = useAsyncData(() => apiFetch<WhatsAppConnection>(`/instances/${instanceId}/whatsapp-connection`), [instanceId]);
  const {
    data: instance,
    error: instanceError,
    loading: instanceLoading,
    reload: reloadInstance,
  } = useAsyncData(() => apiFetch<InstanceDetail>(`/instances/${instanceId}`), [instanceId]);
  const [openProvider, setOpenProvider] = useState<WhatsAppProvider | null>(null);

  const loading = connectionLoading || instanceLoading;
  const loadError = connectionError ?? instanceError;

  if (loading) return <LoadingState />;
  if (loadError) {
    return (
      <ErrorState
        message={loadError}
        onRetry={() => {
          reloadConnection();
          reloadInstance();
        }}
      />
    );
  }
  if (!connection || !instance) return null;

  const effectiveProvider: WhatsAppProvider =
    connection.provider ?? (connection.whatsapp_instance_name ? "evolution" : "whatsbotmais");
  const webhookUrl = typeof window !== "undefined" ? `${window.location.origin}/webhooks/${instance.webhook_token}` : "";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold">Conexao</h1>
        <p className="text-sm text-muted-foreground">
          Escolha como o WhatsApp desta instancia recebe e envia mensagens.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {(Object.keys(PROVIDER_INFO) as WhatsAppProvider[]).map((provider) => {
          const info = PROVIDER_INFO[provider];
          const active = effectiveProvider === provider;
          return (
            <Card key={provider} className={active ? "border-primary" : undefined}>
              <CardHeader>
                <div className="flex items-center justify-between gap-2">
                  <CardTitle>{info.label}</CardTitle>
                  {active ? <Badge>Em uso</Badge> : null}
                </div>
                <CardDescription>{info.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant={active ? "outline" : "default"} size="sm" onClick={() => setOpenProvider(provider)}>
                  {provider === "whatsbotmais" ? "Ver detalhes" : active ? "Gerenciar conexao" : "Conectar"}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Dialog
        open={openProvider !== null}
        onOpenChange={(open) => {
          if (!open) setOpenProvider(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{openProvider ? PROVIDER_INFO[openProvider].label : ""}</DialogTitle>
            <DialogDescription>{openProvider ? PROVIDER_INFO[openProvider].description : ""}</DialogDescription>
          </DialogHeader>
          {openProvider === "whatsbotmais" ? <WhatsBotMaisPanel webhookUrl={webhookUrl} /> : null}
          {openProvider === "evolution" ? (
            <EvolutionPanel instanceId={instanceId} connection={connection} onChanged={reloadConnection} />
          ) : null}
          {openProvider === "meta_cloud" ? (
            <MetaPanel instanceId={instanceId} connection={connection} onChanged={reloadConnection} />
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function WhatsAppConnectionResolvedPage() {
  const { instances, selectedId, error: instancesError, reload: reloadInstances } = useOwnInstances();

  if (instancesError) {
    return <ErrorState message={instancesError} onRetry={reloadInstances} />;
  }
  if (instances === null) {
    return <LoadingState />;
  }
  if (instances.length === 0 || !selectedId) {
    return <EmptyState title="Nenhuma instancia associada a sua conta ainda." icon={Server} />;
  }
  return <WhatsAppConnectionView key={selectedId} instanceId={selectedId} />;
}
