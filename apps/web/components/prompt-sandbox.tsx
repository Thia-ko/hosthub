"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { FormStatus } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { AiAssistSandboxReplyResponse, SandboxMessage } from "@/lib/types";

export function PromptSandbox({ instanceId, promptContent }: { instanceId: string; promptContent: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<SandboxMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const text = input.trim();
    if (!text || loading) return;
    const history = messages;
    setMessages((current) => [...current, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<AiAssistSandboxReplyResponse>(`/instances/${instanceId}/ai-assist/sandbox-reply`, {
        method: "POST",
        body: JSON.stringify({ message: text, prompt_override: promptContent, history }),
      });
      setMessages((current) => [...current, { role: "assistant", content: data.reply }]);
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setMessages([]);
    setError(null);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline">Testar agente</Button>
      </SheetTrigger>
      <SheetContent className="flex w-full flex-col gap-4 overflow-hidden p-6 sm:max-w-lg">
        <SheetHeader className="p-0">
          <SheetTitle>Testar agente</SheetTitle>
        </SheetHeader>
        <p className="text-xs text-muted-foreground">
          Simula uma conversa usando o texto atual do editor, mesmo que ainda nao tenha sido salvo. Consome o
          mesmo limite diario do assistente de IA.
        </p>
        <div className="flex flex-1 flex-col gap-3 overflow-y-auto rounded-md border p-3">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">Envie uma mensagem como se fosse um cliente.</p>
          ) : null}
          {messages.map((message, index) => (
            <div
              key={index}
              className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap",
                message.role === "user"
                  ? "self-end bg-primary text-primary-foreground"
                  : "self-start bg-muted text-foreground"
              )}
            >
              {message.content}
            </div>
          ))}
          {loading ? <p className="self-start text-sm text-muted-foreground">Digitando...</p> : null}
        </div>
        {error ? <FormStatus tone="error">{error}</FormStatus> : null}
        <div className="flex flex-col gap-2">
          <Textarea
            placeholder="Mensagem de teste do cliente..."
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send();
              }
            }}
            className="min-h-20"
          />
          <div className="flex justify-between">
            <Button variant="ghost" size="sm" onClick={reset} disabled={messages.length === 0 || loading}>
              Reiniciar conversa
            </Button>
            <Button size="sm" onClick={send} disabled={loading || !input.trim()}>
              {loading ? "Enviando..." : "Enviar"}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
