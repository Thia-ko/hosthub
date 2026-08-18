"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Webhook } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { MobileCard, MobileCardList } from "@/components/mobile-card";
import { GENERIC_LOAD_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { copyToClipboard } from "@/lib/utils";
import type { WebhookEvent } from "@/lib/types";

const PAGE_SIZE = 50;

function previewPayload(payload: unknown): string {
  const text = JSON.stringify(payload);
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
}

function PayloadDialog({ payload }: { payload: unknown }) {
  return (
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
          {JSON.stringify(payload, null, 2)}
        </pre>
      </DialogContent>
    </Dialog>
  );
}

export function WebhookInspector({
  instanceId,
  webhookUrl,
  headerAction,
}: {
  instanceId: string;
  webhookUrl: string;
  headerAction?: ReactNode;
}) {
  const [events, setEvents] = useState<WebhookEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [copied, setCopied] = useState(false);

  const loadPage = useCallback(
    (offset: number) => {
      const setBusy = offset === 0 ? setLoading : setLoadingMore;
      setBusy(true);
      setError(null);
      apiFetch<WebhookEvent[]>(`/instances/${instanceId}/webhook-events?limit=${PAGE_SIZE}&offset=${offset}`)
        .then((page) => {
          setEvents((current) => (offset === 0 ? page : [...(current ?? []), ...page]));
          setHasMore(page.length === PAGE_SIZE);
        })
        .catch((err: unknown) => setError(errorMessage(err, GENERIC_LOAD_ERROR_MESSAGE)))
        .finally(() => setBusy(false));
    },
    [instanceId]
  );

  useEffect(() => {
    // Fetching on mount is a necessary Effect (react.dev/learn/you-might-not-need-an-effect
    // #fetching-data); loadPage resets loading/error synchronously before the fetch settles,
    // which set-state-in-effect can't distinguish from a derived-state anti-pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadPage(0);
  }, [loadPage]);

  async function copyUrl() {
    if (!(await copyToClipboard(webhookUrl))) return;
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">URL do webhook</p>
          {headerAction}
        </div>
        <div className="flex items-center gap-2">
          <code className="break-all rounded-md border bg-muted/40 px-3 py-1.5 text-xs">{webhookUrl}</code>
          <Button variant="outline" size="sm" onClick={copyUrl}>
            {copied ? "Copiado" : "Copiar"}
          </Button>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Eventos recebidos</p>
        <Button variant="outline" size="sm" onClick={() => loadPage(0)}>
          Atualizar
        </Button>
      </div>

      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={() => loadPage(0)} /> : null}
      {!loading && !error && events && events.length === 0 ? (
        <EmptyState title="Nenhum evento recebido ainda." icon={Webhook} />
      ) : null}
      {!loading && !error && events && events.length > 0 ? (
        <>
          <MobileCardList>
            {events.map((event) => (
              <MobileCard key={event.id}>
                <p className="text-sm font-medium">{new Date(event.received_at).toLocaleString("pt-BR")}</p>
                <p className="break-all font-mono text-xs text-muted-foreground">
                  {previewPayload(event.payload_json)}
                </p>
                <div className="flex justify-end">
                  <PayloadDialog payload={event.payload_json} />
                </div>
              </MobileCard>
            ))}
          </MobileCardList>
          <div className="hidden sm:block">
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
                      <PayloadDialog payload={event.payload_json} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {hasMore ? (
            <Button variant="outline" size="sm" className="w-fit" disabled={loadingMore} onClick={() => loadPage(events.length)}>
              {loadingMore ? "Carregando..." : "Carregar mais"}
            </Button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
