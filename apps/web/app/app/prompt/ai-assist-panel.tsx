"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { DiffView } from "@/components/diff-view";
import { apiFetch, ApiError } from "@/lib/api-client";
import type { AiAssistSuggestResponse, AiAssistUsage } from "@/lib/types";

export function AiAssistPanel({
  instanceId,
  currentContent,
  onApplied,
}: {
  instanceId: string;
  currentContent: string;
  onApplied: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [usage, setUsage] = useState<AiAssistUsage | null>(null);
  const [instruction, setInstruction] = useState("");
  const [suggestion, setSuggestion] = useState<AiAssistSuggestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    apiFetch<AiAssistUsage>(`/instances/${instanceId}/ai-assist/usage`).then(setUsage);
  }, [open, instanceId]);

  const overLimit = usage ? usage.used_today >= usage.limit : false;

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<AiAssistSuggestResponse>(`/instances/${instanceId}/ai-assist/suggest`, {
        method: "POST",
        body: JSON.stringify({ instruction }),
      });
      setSuggestion(result);
      apiFetch<AiAssistUsage>(`/instances/${instanceId}/ai-assist/usage`).then(setUsage);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nao foi possivel gerar a sugestao");
    } finally {
      setLoading(false);
    }
  }

  async function handleApply() {
    if (!suggestion) return;
    setLoading(true);
    try {
      await apiFetch(`/instances/${instanceId}/ai-assist/suggest/${suggestion.ai_assist_request_id}/apply`, {
        method: "POST",
      });
      setSuggestion(null);
      setInstruction("");
      setOpen(false);
      onApplied();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nao foi possivel aplicar a sugestao");
    } finally {
      setLoading(false);
    }
  }

  async function handleDiscard() {
    if (!suggestion) return;
    await apiFetch(`/instances/${instanceId}/ai-assist/suggest/${suggestion.ai_assist_request_id}/discard`, {
      method: "POST",
    });
    setSuggestion(null);
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline">Assistente de IA</Button>
      </SheetTrigger>
      <SheetContent className="w-full gap-4 overflow-y-auto p-6 sm:max-w-lg">
        <SheetHeader className="p-0">
          <SheetTitle>Assistente de IA</SheetTitle>
        </SheetHeader>
        {usage ? (
          <div className="flex flex-col gap-1.5">
            <p className="text-xs text-muted-foreground">
              Uso hoje: {usage.used_today} / {usage.limit} tokens
            </p>
            <Progress value={Math.min(100, (usage.used_today / usage.limit) * 100)} />
            {overLimit ? (
              <p className="text-xs text-destructive">
                Limite atingido. Reinicia em {new Date(usage.resets_at).toLocaleString("pt-BR")}.
              </p>
            ) : null}
          </div>
        ) : null}

        {!suggestion ? (
          <div className="flex flex-col gap-3">
            <Textarea
              placeholder="Descreva a alteracao desejada no prompt..."
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              className="min-h-32"
            />
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <Button onClick={handleGenerate} disabled={loading || overLimit || !instruction}>
              {loading ? "Gerando..." : "Gerar sugestao"}
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">Pre-visualizacao da alteracao sugerida:</p>
            <DiffView from={currentContent} to={suggestion.suggested_content} />
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <div className="flex gap-2">
              <Button onClick={handleApply} disabled={loading}>
                Aplicar
              </Button>
              <Button onClick={handleDiscard} variant="outline" disabled={loading}>
                Descartar
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
