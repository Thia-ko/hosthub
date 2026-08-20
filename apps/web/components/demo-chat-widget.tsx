"use client";

import { useRef, useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { apiFetch, errorMessage, ApiError } from "@/lib/api-client";
import { cn, randomId } from "@/lib/utils";
import { BrandMark } from "@/components/brand-mark";
import { DemoLeadForm } from "@/components/demo-lead-form";

const MAX_MESSAGES = 6;

interface DemoChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

interface DemoChatResponse {
  reply: string;
  messages_remaining: number;
}

export function DemoChatWidget() {
  const [messages, setMessages] = useState<DemoChatHistoryItem[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [remaining, setRemaining] = useState(MAX_MESSAGES);
  const sessionId = useRef<string>(undefined);
  if (sessionId.current == null) sessionId.current = randomId();

  async function handleSend() {
    const trimmed = input.trim();
    if (remaining <= 0 || loading || !trimmed) return;

    setLoading(true);
    try {
      const res = await apiFetch<DemoChatResponse>("/demo/chat", {
        method: "POST",
        body: JSON.stringify({
          session_id: sessionId.current,
          message: trimmed,
          history: messages.slice(-12).map((m) => ({ role: m.role, content: m.content })),
        }),
      });
      setMessages((current) => [
        ...current,
        { role: "user", content: trimmed },
        { role: "assistant", content: res.reply },
      ]);
      setRemaining(res.messages_remaining);
      setInput("");
    } catch (err) {
      toast.error(errorMessage(err, "Nao foi possivel enviar sua mensagem."));
      if (err instanceof ApiError && err.status === 429) {
        setRemaining(0);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          Mensagens restantes: {remaining}/{MAX_MESSAGES}
        </Badge>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex max-h-80 flex-col gap-2 overflow-y-auto">
          {messages.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Envie uma mensagem para começar a conversa com o agente de demonstração.
            </p>
          ) : null}
          {messages.map((message, index) => (
            <div key={index} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
              <div
                className={cn(
                  "flex max-w-[80%] flex-col gap-1 rounded-2xl px-3 py-2 text-sm",
                  message.role === "user" ? "rounded-br-sm bg-primary text-primary-foreground" : "rounded-bl-sm bg-muted"
                )}
              >
                <span className="whitespace-pre-wrap break-words">{message.content}</span>
              </div>
            </div>
          ))}
          {loading ? (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-muted px-3 py-2">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
                  <BrandMark active className="size-3" />
                </span>
                <span className="text-xs text-muted-foreground">Pensando...</span>
              </div>
            </div>
          ) : null}
        </div>
        <p className="text-xs text-muted-foreground">Demonstração com dados fictícios — não é sua IA real.</p>
        {remaining > 0 ? (
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Digite sua mensagem..."
              disabled={loading}
            />
            <Button onClick={handleSend} disabled={loading || !input.trim()} size="icon" aria-label="Enviar">
              <Send className="size-4" />
            </Button>
          </div>
        ) : null}
      </CardContent>
      {remaining <= 0 ? (
        <CardFooter className="flex flex-col items-stretch gap-3 border-t pt-4">
          <DemoLeadForm />
        </CardFooter>
      ) : null}
    </Card>
  );
}
