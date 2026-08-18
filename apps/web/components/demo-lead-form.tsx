"use client";

import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FormStatus } from "@/components/state";
import { apiFetch, errorMessage } from "@/lib/api-client";

export function DemoLeadForm({ onSubmitted }: { onSubmitted?: () => void }) {
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [note, setNote] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiFetch("/demo/leads", {
        method: "POST",
        body: JSON.stringify({
          name,
          contact,
          business_name: businessName || null,
          note: note || null,
        }),
      });
      setSubmitted(true);
      toast.success("Recebemos seus dados! Nosso time vai entrar em contato.");
      onSubmitted?.();
    } catch (err) {
      setError(errorMessage(err, "Nao foi possivel enviar. Tente novamente."));
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return <FormStatus tone="success">Obrigado! Nosso time vai te chamar no WhatsApp/e-mail informado.</FormStatus>;
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <p className="text-sm font-medium">Gostou? Deixe seus dados que nosso time te chama.</p>
      <Input placeholder="Seu nome" value={name} onChange={(e) => setName(e.target.value)} required />
      <Input
        placeholder="WhatsApp ou e-mail"
        value={contact}
        onChange={(e) => setContact(e.target.value)}
        required
      />
      <Input
        placeholder="Nome do negócio (opcional)"
        value={businessName}
        onChange={(e) => setBusinessName(e.target.value)}
      />
      <Textarea
        placeholder="O que você gostaria de automatizar?"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      <Button type="submit" disabled={loading}>
        Quero uma demonstração para o meu negócio
      </Button>
    </form>
  );
}
