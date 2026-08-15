"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DiffView } from "@/components/diff-view";
import { FormStatus } from "@/components/state";
import { apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { PromptVersionDetail } from "@/lib/types";

/** Surfaces a prompt version the auto-generation pipeline created from analyzed conversations
 * (`PromptVersion.is_pending`). It never goes live on its own - a human must approve or reject
 * it here before it can replace the active prompt. */
export function PendingPromptBanner({
  instanceId,
  currentContent,
  onResolved,
}: {
  instanceId: string;
  currentContent: string;
  onResolved: () => void;
}) {
  const {
    data: pending,
    loading,
    reload,
  } = useAsyncData(
    () => apiFetch<PromptVersionDetail | null>(`/instances/${instanceId}/analytics/pending-prompt`),
    [instanceId]
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading || !pending) return null;

  async function approve() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/instances/${instanceId}/analytics/pending-prompt/${pending!.id}/approve`, { method: "POST" });
      toast.success(`Prompt v${pending!.version_number} aprovado e ativado.`);
      reload();
      onResolved();
    } catch (err) {
      setError(errorMessage(err, "Nao foi possivel aprovar o prompt gerado."));
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/instances/${instanceId}/analytics/pending-prompt/${pending!.id}/reject`, { method: "POST" });
      toast.success("Prompt gerado descartado.");
      reload();
    } catch (err) {
      setError(errorMessage(err, "Nao foi possivel descartar o prompt gerado."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="border-primary/40">
      <CardHeader>
        <CardTitle className="text-base">
          Prompt gerado automaticamente (v{pending.version_number}) aguardando aprovacao
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">
          {pending.change_note ?? "Gerado a partir dos dados coletados das conversas."} Revise as diferencas antes
          de aprovar - ele so entra em uso apos sua confirmacao.
        </p>
        <DiffView from={currentContent} to={pending.content} />
        {error ? <FormStatus tone="error">{error}</FormStatus> : null}
        <div className="flex gap-2">
          <Button onClick={approve} disabled={busy}>
            Aprovar e ativar
          </Button>
          <Button onClick={reject} variant="outline" disabled={busy}>
            Descartar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
