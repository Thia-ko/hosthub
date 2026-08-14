"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { AiSettings } from "@/lib/types";

const SOURCE_LABEL: Record<AiSettings["api_key_source"], string> = {
  database: "Configurada no painel administrativo",
  env: "Configurada via variavel de ambiente (.env)",
  none: "Nao configurada",
};

export default function AdminAiSettingsView() {
  const { data: fetched, error, loading, reload } = useAsyncData(() => apiFetch<AiSettings>("/ai-settings"), []);
  const [syncedFetched, setSyncedFetched] = useState<AiSettings | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [transcribeModel, setTranscribeModel] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [source, setSource] = useState<AiSettings["api_key_source"]>("none");
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  if (fetched && fetched !== syncedFetched) {
    setSyncedFetched(fetched);
    setBaseUrl(fetched.base_url);
    setModel(fetched.model);
    setTranscribeModel(fetched.transcribe_model);
    setSource(fetched.api_key_source);
    setApiKeyInput("");
  }

  async function persist(body: {
    base_url: string;
    model: string;
    transcribe_model: string;
    api_key?: string | null;
    clear_api_key?: boolean;
  }) {
    setSaving(true);
    setSaveStatus(null);
    try {
      const updated = await apiFetch<AiSettings>("/ai-settings", { method: "PUT", body: JSON.stringify(body) });
      setBaseUrl(updated.base_url);
      setModel(updated.model);
      setTranscribeModel(updated.transcribe_model);
      setSource(updated.api_key_source);
      setApiKeyInput("");
      setSaveStatus({ tone: "success", text: "Configuracoes de IA salvas." });
    } catch (err) {
      setSaveStatus({ tone: "error", text: errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE) });
    } finally {
      setSaving(false);
    }
  }

  function handleSave() {
    persist({
      base_url: baseUrl,
      model,
      transcribe_model: transcribeModel,
      api_key: apiKeyInput || undefined,
    });
  }

  function handleRemoveKey() {
    persist({ base_url: baseUrl, model, transcribe_model: transcribeModel, clear_api_key: true });
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!syncedFetched) return null;

  return (
    <div className="flex max-w-lg flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="aiApiKey">Chave de API</Label>
        <Input
          id="aiApiKey"
          type="password"
          autoComplete="off"
          placeholder={source === "none" ? "sk-..." : "Deixe em branco para manter a chave atual"}
          value={apiKeyInput}
          onChange={(event) => setApiKeyInput(event.target.value)}
        />
        <p className="text-xs text-muted-foreground">{SOURCE_LABEL[source]}</p>
        {source === "database" ? (
          <Button variant="outline" size="sm" className="w-fit" onClick={handleRemoveKey} disabled={saving}>
            Remover chave
          </Button>
        ) : null}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="aiBaseUrl">URL base (compativel com Chat Completions da OpenAI)</Label>
        <Input id="aiBaseUrl" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="aiModel">Modelo de chat/visao</Label>
        <Input id="aiModel" value={model} onChange={(event) => setModel(event.target.value)} />
        <p className="text-xs text-muted-foreground">
          Usado para sugestoes de prompt e para responder o cliente (precisa suportar visao para
          descrever imagens recebidas no WhatsApp).
        </p>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="aiTranscribeModel">Modelo de transcricao de audio</Label>
        <Input
          id="aiTranscribeModel"
          value={transcribeModel}
          onChange={(event) => setTranscribeModel(event.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Endpoint /audio/transcriptions, padrao Whisper - troque se o provedor usar outro nome.
        </p>
      </div>
      {saveStatus ? <FormStatus tone={saveStatus.tone}>{saveStatus.text}</FormStatus> : null}
      <Button onClick={handleSave} disabled={saving} className="w-fit">
        {saving ? "Salvando..." : "Salvar alteracoes"}
      </Button>
    </div>
  );
}
