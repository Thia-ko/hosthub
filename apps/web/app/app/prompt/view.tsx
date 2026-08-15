"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_LOAD_ERROR_MESSAGE, GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useOwnInstances } from "@/lib/instance-context";
import type { PromptVersionDetail } from "@/lib/types";
import { AiAssistPanel } from "./ai-assist-panel";
import { PendingPromptBanner } from "./pending-prompt-banner";
import { PromptSandbox } from "@/components/prompt-sandbox";
import { PENDING_TEMPLATE_KEY } from "@/lib/constants";

export default function PromptEditorView() {
  const { instances, selectedId, error: instancesError, reload: reloadInstances } = useOwnInstances();
  const [current, setCurrent] = useState<PromptVersionDetail | null>(null);
  const [content, setContent] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [pendingSource, setPendingSource] = useState<"manual" | "template">("manual");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const loadCurrentVersion = useCallback((instanceId: string) => {
    setLoading(true);
    setLoadError(null);
    apiFetch<PromptVersionDetail[]>(`/instances/${instanceId}/prompt-versions`)
      .then((versions) => {
        const latest = versions[0];
        if (!latest) {
          setCurrent(null);
          setContent("");
          return;
        }
        return apiFetch<PromptVersionDetail>(`/instances/${instanceId}/prompt-versions/${latest.id}`).then(
          (detail) => {
            setCurrent(detail);
            setContent(detail.content);
          }
        );
      })
      .catch((err: unknown) => {
        setLoadError(errorMessage(err, GENERIC_LOAD_ERROR_MESSAGE));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    const pending = sessionStorage.getItem(PENDING_TEMPLATE_KEY);
    if (pending) {
      const { content: templateContent, title } = JSON.parse(pending) as { content: string; title: string };
      setContent(templateContent);
      setChangeNote(`Template: ${title}`);
      setPendingSource("template");
      sessionStorage.removeItem(PENDING_TEMPLATE_KEY);
      setLoading(false);
      return;
    }
    loadCurrentVersion(selectedId);
  }, [selectedId, loadCurrentVersion]);

  async function handleSave() {
    if (!selectedId) return;
    setSaving(true);
    setSaveStatus(null);
    try {
      const version = await apiFetch<PromptVersionDetail>(`/instances/${selectedId}/prompt-versions`, {
        method: "POST",
        body: JSON.stringify({ content, change_note: changeNote || null, source: pendingSource }),
      });
      setCurrent(version);
      setChangeNote("");
      setPendingSource("manual");
      setSaveStatus({ tone: "success", text: `Versao ${version.version_number} salva.` });
    } catch (err) {
      setSaveStatus({ tone: "error", text: errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE) });
    } finally {
      setSaving(false);
    }
  }

  if (instancesError) {
    return <ErrorState message={instancesError} onRetry={reloadInstances} />;
  }

  if (instances === null) {
    return <LoadingState />;
  }

  if (instances.length === 0) {
    return <EmptyState title="Nenhuma instancia associada a sua conta ainda." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Prompt da IA</h1>
        {selectedId ? (
          <div className="flex items-center gap-2">
            <PromptSandbox instanceId={selectedId} promptContent={content} />
            <AiAssistPanel
              instanceId={selectedId}
              currentContent={content}
              onApplied={() => loadCurrentVersion(selectedId)}
            />
          </div>
        ) : null}
      </div>
      {loading ? <LoadingState /> : null}
      {!loading && loadError ? (
        <ErrorState message={loadError} onRetry={() => selectedId && loadCurrentVersion(selectedId)} />
      ) : null}
      {!loading && !loadError ? (
        <>
          {selectedId ? (
            <PendingPromptBanner
              instanceId={selectedId}
              currentContent={current?.content ?? ""}
              onResolved={() => loadCurrentVersion(selectedId)}
            />
          ) : null}
          <p className="text-sm text-muted-foreground">
            {current ? `Versao atual: ${current.version_number}` : "Nenhuma versao salva ainda."}
          </p>
          <Textarea
            className="min-h-96 font-mono text-sm"
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="changeNote">Nota da alteracao (opcional)</Label>
            <Input id="changeNote" value={changeNote} onChange={(event) => setChangeNote(event.target.value)} />
          </div>
          {saveStatus ? <FormStatus tone={saveStatus.tone}>{saveStatus.text}</FormStatus> : null}
          <Button onClick={handleSave} disabled={saving || !content} className="w-fit">
            {saving ? "Salvando..." : "Salvar nova versao"}
          </Button>
        </>
      ) : null}
    </div>
  );
}
