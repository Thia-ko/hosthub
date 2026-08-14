"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Image as ImageIcon, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { GENERIC_LOAD_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { ConversationMessage, ConversationSummary, MessageKind } from "@/lib/types";

const PAGE_SIZE = 50;

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function KindIcon({ kind, className }: { kind: MessageKind; className?: string }) {
  if (kind === "audio") return <Mic className={className} />;
  if (kind === "image") return <ImageIcon className={className} />;
  return null;
}

function kindLabel(kind: MessageKind): string | null {
  if (kind === "audio") return "Audio (transcrito)";
  if (kind === "image") return "Imagem";
  return null;
}

function ConversationListItem({
  conversation,
  active,
  onClick,
}: {
  conversation: ConversationSummary;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full flex-col gap-1 rounded-lg border px-3 py-2.5 text-left transition-colors",
        active ? "border-primary bg-primary/5" : "border-transparent hover:bg-muted/50"
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-medium">{conversation.sender_number}</span>
        <span className="shrink-0 text-xs text-muted-foreground">
          {formatDateTime(conversation.last_message_at)}
        </span>
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {conversation.last_direction === "outbound" ? <span className="shrink-0">Voce:</span> : null}
        <KindIcon kind={conversation.last_message_kind} className="size-3 shrink-0" />
        <span className="truncate">{conversation.last_message_text || "(sem texto)"}</span>
      </div>
    </button>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const outbound = message.direction === "outbound";
  const label = kindLabel(message.kind);
  return (
    <div className={cn("flex", outbound ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "flex max-w-[80%] flex-col gap-1 rounded-2xl px-3 py-2 text-sm",
          outbound ? "rounded-br-sm bg-primary text-primary-foreground" : "rounded-bl-sm bg-muted"
        )}
      >
        {label ? (
          <span
            className={cn(
              "flex items-center gap-1 text-xs font-medium",
              outbound ? "text-primary-foreground/80" : "text-muted-foreground"
            )}
          >
            <KindIcon kind={message.kind} className="size-3" />
            {label}
          </span>
        ) : null}
        <span className="whitespace-pre-wrap break-words">{message.text || "(sem texto)"}</span>
        <span
          className={cn(
            "self-end text-[10px]",
            outbound ? "text-primary-foreground/70" : "text-muted-foreground"
          )}
        >
          {formatDateTime(message.created_at)}
        </span>
      </div>
    </div>
  );
}

function ConversationThread({ instanceId, senderNumber }: { instanceId: string; senderNumber: string }) {
  const [messages, setMessages] = useState<ConversationMessage[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);

  const loadOlder = useCallback(
    (offset: number) => {
      const setBusy = offset === 0 ? setLoading : setLoadingMore;
      setBusy(true);
      setError(null);
      apiFetch<ConversationMessage[]>(
        `/instances/${instanceId}/conversations/${encodeURIComponent(senderNumber)}?limit=${PAGE_SIZE}&offset=${offset}`
      )
        .then((page) => {
          // API returns newest-first per page; reverse to chronological order and prepend
          // (this page is older than whatever is already loaded).
          const chronological = [...page].reverse();
          setMessages((current) => (offset === 0 ? chronological : [...chronological, ...(current ?? [])]));
          setHasMore(page.length === PAGE_SIZE);
        })
        .catch((err: unknown) => setError(errorMessage(err, GENERIC_LOAD_ERROR_MESSAGE)))
        .finally(() => setBusy(false));
    },
    [instanceId, senderNumber]
  );

  useEffect(() => {
    loadOlder(0);
  }, [loadOlder]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={() => loadOlder(0)} />;
  if (!messages || messages.length === 0) {
    return <EmptyState title="Nenhuma mensagem nesta conversa ainda." />;
  }

  return (
    <div className="flex flex-col gap-3">
      {hasMore ? (
        <Button
          variant="outline"
          size="sm"
          className="w-fit self-center"
          disabled={loadingMore}
          onClick={() => loadOlder(messages.length)}
        >
          {loadingMore ? "Carregando..." : "Carregar mensagens antigas"}
        </Button>
      ) : null}
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}

export function ConversationView({ instanceId }: { instanceId: string }) {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);

  const loadPage = useCallback(
    (offset: number) => {
      const setBusy = offset === 0 ? setLoading : setLoadingMore;
      setBusy(true);
      setError(null);
      apiFetch<ConversationSummary[]>(`/instances/${instanceId}/conversations?limit=${PAGE_SIZE}&offset=${offset}`)
        .then((page) => {
          setConversations((current) => (offset === 0 ? page : [...(current ?? []), ...page]));
          setHasMore(page.length === PAGE_SIZE);
        })
        .catch((err: unknown) => setError(errorMessage(err, GENERIC_LOAD_ERROR_MESSAGE)))
        .finally(() => setBusy(false));
    },
    [instanceId]
  );

  useEffect(() => {
    loadPage(0);
  }, [loadPage]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={() => loadPage(0)} />;
  if (!conversations || conversations.length === 0) {
    return (
      <EmptyState
        title="Nenhuma conversa ainda."
        description="As conversas aparecem aqui assim que o WhatsApp da instancia comecar a receber mensagens."
      />
    );
  }

  return (
    <div className="flex flex-col gap-4 md:flex-row">
      <div className={cn("flex flex-col gap-1 md:w-80 md:shrink-0", selected && "hidden md:flex")}>
        {conversations.map((conversation) => (
          <ConversationListItem
            key={conversation.sender_number}
            conversation={conversation}
            active={conversation.sender_number === selected}
            onClick={() => setSelected(conversation.sender_number)}
          />
        ))}
        {hasMore ? (
          <Button
            variant="outline"
            size="sm"
            className="w-fit"
            disabled={loadingMore}
            onClick={() => loadPage(conversations.length)}
          >
            {loadingMore ? "Carregando..." : "Carregar mais conversas"}
          </Button>
        ) : null}
      </div>
      <div className={cn("min-w-0 flex-1 rounded-lg border p-3", !selected && "hidden md:flex md:items-center md:justify-center")}>
        {selected ? (
          <div className="flex w-full flex-col gap-3">
            <Button variant="ghost" size="sm" className="w-fit md:hidden" onClick={() => setSelected(null)}>
              <ArrowLeft className="size-4" />
              Conversas
            </Button>
            <ConversationThread instanceId={instanceId} senderNumber={selected} />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Selecione uma conversa para ver o historico.</p>
        )}
      </div>
    </div>
  );
}
