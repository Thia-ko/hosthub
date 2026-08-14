"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { FormStatus } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";

export function RegenerateWebhookTokenButton({
  instanceId,
  onRegenerated,
}: {
  instanceId: string;
  onRegenerated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConfirm() {
    setLoading(true);
    setError(null);
    try {
      await apiFetch(`/instances/${instanceId}/regenerate-webhook-token`, { method: "POST" });
      onRegenerated();
      setOpen(false);
      toast.success("Nova URL de webhook gerada.");
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Gerar nova URL
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Gerar nova URL de webhook</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          A URL atual para de funcionar imediatamente. Atualize a configuracao no WhatsBotMais (ou onde ela
          estiver cadastrada) com a nova URL antes de sair desta tela.
        </p>
        {error ? <FormStatus tone="error">{error}</FormStatus> : null}
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={loading}>
            {loading ? "Gerando..." : "Confirmar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
