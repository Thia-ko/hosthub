"use client";

import { useState } from "react";
import { copyToClipboard } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Documentacao da API publica (Bearer API key) para uma equipe de desenvolvimento propria ou
 * automacao (n8n, backend do cliente) integrar sem depender de um login de usuario. Ver
 * app.api.v1.routers.external e ApiKeysPanel (criacao/revogacao das chaves logo abaixo).
 */
export function ExternalApiDocs() {
  const [copied, setCopied] = useState(false);
  const baseUrl = typeof window !== "undefined" ? `${window.location.origin}/api/v1/external` : "/api/v1/external";

  async function copyBaseUrl() {
    if (!(await copyToClipboard(baseUrl))) return;
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>API externa (n8n / equipe de desenvolvimento)</CardTitle>
        <CardDescription>
          Para quem quer integrar por conta propria em vez de usar o painel: crie uma API key abaixo e autentique
          cada chamada com <code className="text-xs">Authorization: Bearer &lt;chave&gt;</code>. Uma chave so
          consegue fazer o que suas permissoes autorizam, e pode ser revogada a qualquer momento sem afetar as
          outras.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm">
        <div className="flex items-center gap-2">
          <code className="break-all rounded-md border bg-muted/40 px-3 py-1.5 text-xs">{baseUrl}</code>
          <Button variant="outline" size="sm" onClick={copyBaseUrl}>
            {copied ? "Copiado" : "Copiar"}
          </Button>
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="font-medium">
            GET /prompt <span className="font-normal text-muted-foreground">(permissao prompt:read)</span>
          </p>
          <p className="text-muted-foreground">
            Retorna o prompt ativo da instancia: <code className="text-xs">prompt</code>,{" "}
            <code className="text-xs">version_number</code>, <code className="text-xs">status</code>. Use para
            manter o system prompt de um agente proprio sempre sincronizado.
          </p>
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="font-medium">
            GET /data <span className="font-normal text-muted-foreground">(permissao data:read)</span>
          </p>
          <p className="text-muted-foreground">
            Retorna os dados que a IA coletou sobre o negocio: informacoes gerais, produtos/servicos, politicas e
            FAQs.
          </p>
        </div>
        <div className="flex flex-col gap-1.5">
          <p className="font-medium">
            POST /messages <span className="font-normal text-muted-foreground">(permissao messages:write)</span>
          </p>
          <p className="text-muted-foreground">
            Envia uma mensagem no WhatsApp da instancia. Corpo: <code className="text-xs">{"{ \"to\": \"5511999999999\", \"text\": \"...\" }"}</code>.
            Pausa a resposta automatica da IA na conversa, como uma resposta manual feita aqui no painel.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
