"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiFetch } from "@/lib/api-client";
import type { WebhookEvent } from "@/lib/types";

function previewPayload(payload: unknown): string {
  const text = JSON.stringify(payload);
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
}

export function WebhookInspector({ instanceId, webhookUrl }: { instanceId: string; webhookUrl: string }) {
  const [events, setEvents] = useState<WebhookEvent[]>([]);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    apiFetch<WebhookEvent[]>(`/instances/${instanceId}/webhook-events`).then(setEvents);
  }, [instanceId]);

  useEffect(() => {
    load();
  }, [load]);

  function copyUrl() {
    navigator.clipboard.writeText(webhookUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <p className="text-sm font-medium">URL do webhook</p>
        <div className="flex items-center gap-2">
          <code className="break-all rounded-md border bg-muted/40 px-3 py-1.5 text-xs">{webhookUrl}</code>
          <Button variant="outline" size="sm" onClick={copyUrl}>
            {copied ? "Copiado" : "Copiar"}
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Eventos recebidos</p>
        <Button variant="outline" size="sm" onClick={load}>
          Atualizar
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Recebido em</TableHead>
            <TableHead>Payload</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {events.map((event) => (
            <TableRow key={event.id}>
              <TableCell>{new Date(event.received_at).toLocaleString("pt-BR")}</TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {previewPayload(event.payload_json)}
              </TableCell>
              <TableCell>
                <Dialog>
                  <DialogTrigger asChild>
                    <Button variant="ghost" size="sm">
                      Ver JSON
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl">
                    <DialogHeader>
                      <DialogTitle>Payload recebido</DialogTitle>
                    </DialogHeader>
                    <pre className="max-h-96 overflow-auto rounded-md bg-muted/40 p-3 text-xs">
                      {JSON.stringify(event.payload_json, null, 2)}
                    </pre>
                  </DialogContent>
                </Dialog>
              </TableCell>
            </TableRow>
          ))}
          {events.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3} className="text-center text-muted-foreground">
                Nenhum evento recebido ainda.
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}
