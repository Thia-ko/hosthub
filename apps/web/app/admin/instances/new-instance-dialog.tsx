"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FormStatus } from "@/components/state";
import { apiFetch, errorMessage } from "@/lib/api-client";
import type { InstanceCreateResponse } from "@/lib/types";

export function NewInstanceDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientFullName, setClientFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [createdPassword, setCreatedPassword] = useState<{ email: string; password: string } | null>(null);

  function resetForm() {
    setName("");
    setClientEmail("");
    setClientFullName("");
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const response = await apiFetch<InstanceCreateResponse>("/instances", {
        method: "POST",
        body: JSON.stringify({ name, client_email: clientEmail, client_full_name: clientFullName }),
      });
      onCreated();
      if (response.generated_password) {
        setCreatedPassword({ email: response.client_email, password: response.generated_password });
      } else {
        setOpen(false);
        resetForm();
      }
    } catch (err) {
      setError(errorMessage(err, "Nao foi possivel criar a instancia."));
    } finally {
      setLoading(false);
    }
  }

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      resetForm();
      setCreatedPassword(null);
    }
  }

  if (createdPassword) {
    return (
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogTrigger asChild>
          <Button>Nova instancia</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Instancia criada</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Compartilhe estas credenciais com o cliente. A senha nao sera exibida novamente.
          </p>
          <div className="flex flex-col gap-2 rounded-md border bg-muted/40 p-3 text-sm">
            <span>
              <strong>E-mail:</strong> {createdPassword.email}
            </span>
            <span>
              <strong>Senha:</strong> {createdPassword.password}
            </span>
          </div>
          <DialogFooter>
            <Button
              onClick={() => navigator.clipboard.writeText(createdPassword.password)}
              variant="outline"
            >
              Copiar senha
            </Button>
            <Button onClick={() => handleOpenChange(false)}>Fechar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>Nova instancia</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nova instancia</DialogTitle>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name">Nome da instancia</Label>
            <Input id="name" required value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="client_email">E-mail do cliente</Label>
            <Input
              id="client_email"
              type="email"
              required
              value={clientEmail}
              onChange={(event) => setClientEmail(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="client_full_name">Nome do cliente</Label>
            <Input
              id="client_full_name"
              required
              value={clientFullName}
              onChange={(event) => setClientFullName(event.target.value)}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Uma senha sera gerada automaticamente para um cliente novo.
          </p>
          {error ? <FormStatus tone="error">{error}</FormStatus> : null}
          <DialogFooter>
            <Button type="submit" disabled={loading}>
              {loading ? "Criando..." : "Criar instancia"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
