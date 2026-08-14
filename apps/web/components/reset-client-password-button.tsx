"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { FormStatus } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import type { ClientPasswordResetOut } from "@/lib/types";

export function ResetClientPasswordButton({ instanceId, clientEmail }: { instanceId: string; clientEmail: string }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ClientPasswordResetOut | null>(null);

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      setResult(null);
      setError(null);
    }
  }

  async function handleConfirm() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ClientPasswordResetOut>(`/instances/${instanceId}/reset-client-password`, {
        method: "POST",
      });
      setResult(data);
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-fit">
          Redefinir senha do cliente
        </Button>
      </DialogTrigger>
      <DialogContent>
        {result ? (
          <>
            <DialogHeader>
              <DialogTitle>Senha redefinida</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-muted-foreground">
              Compartilhe esta nova senha com o cliente. Ela nao sera exibida novamente.
            </p>
            <div className="flex flex-col gap-2 rounded-md border bg-muted/40 p-3 text-sm">
              <span>
                <strong>E-mail:</strong> {result.client_email}
              </span>
              <span>
                <strong>Senha:</strong> {result.generated_password}
              </span>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => navigator.clipboard.writeText(result.generated_password)}>
                Copiar senha
              </Button>
              <Button onClick={() => handleOpenChange(false)}>Fechar</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Redefinir senha do cliente</DialogTitle>
            </DialogHeader>
            <p className="text-sm text-muted-foreground">
              Uma nova senha sera gerada para <strong>{clientEmail}</strong>. A senha atual deixa de funcionar
              imediatamente.
            </p>
            {error ? <FormStatus tone="error">{error}</FormStatus> : null}
            <DialogFooter>
              <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={loading}>
                Cancelar
              </Button>
              <Button onClick={handleConfirm} disabled={loading}>
                {loading ? "Redefinindo..." : "Confirmar"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
