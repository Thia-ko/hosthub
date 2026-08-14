"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Documentação de integração com n8n enquanto o HostHub não assume o atendimento diretamente.
 * Remover quando o motor de conversas passar a rodar dentro do HostHub.
 */
export function WebhookIntegrationDocs({ webhookUrl }: { webhookUrl: string }) {
  const [copied, setCopied] = useState(false);
  const promptUrl = `${webhookUrl}/prompt`;

  function copyPromptUrl() {
    navigator.clipboard.writeText(promptUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Integracao com n8n</CardTitle>
        <CardDescription>
          Enquanto o atendimento roda no n8n, use esta URL para manter o prompt sempre atualizado sem copiar e
          colar manualmente.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <div className="flex flex-col gap-1.5">
          <p className="font-medium">1. Buscar o prompt ativo antes de chamar o modelo</p>
          <p className="text-muted-foreground">
            Adicione um node HTTP Request (GET) antes do node que chama a IA, apontando para:
          </p>
          <div className="flex items-center gap-2">
            <code className="break-all rounded-md border bg-muted/40 px-3 py-1.5 text-xs">{promptUrl}</code>
            <Button variant="outline" size="sm" onClick={copyPromptUrl}>
              {copied ? "Copiado" : "Copiar"}
            </Button>
          </div>
          <p className="text-muted-foreground">
            A resposta traz <code className="text-xs">prompt</code> (texto atual), <code className="text-xs">status</code>{" "}
            (<code className="text-xs">active</code> / <code className="text-xs">paused</code> /{" "}
            <code className="text-xs">archived</code>) e <code className="text-xs">version_number</code>. Use o campo{" "}
            <code className="text-xs">prompt</code> como system prompt; se <code className="text-xs">status</code> vier
            diferente de <code className="text-xs">active</code>, encerre o fluxo sem responder — assim pausar a
            instancia aqui no painel pausa o agente de verdade, sem mexer no n8n.
          </p>
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="font-medium">2. Opcional: refletir os eventos aqui no painel</p>
          <p className="text-muted-foreground">
            A lista de “Eventos recebidos” abaixo so mostra o que chega na URL do webhook desta instancia (ao lado).
            Se quiser ver o atendimento real aqui, adicione mais um node no n8n fazendo um POST (fire-and-forget) para
            essa mesma URL.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
