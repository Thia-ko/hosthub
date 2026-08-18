"use client";

import { Server } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AiPipelinePreview } from "@/components/ai-pipeline-preview";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { GENERIC_LOAD_ERROR_MESSAGE, GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import { useOwnInstances } from "@/lib/instance-context";
import type { PromptVersionDetail } from "@/lib/types";
import { AiAssistPanel } from "./ai-assist-panel";
import { GuidedWizard } from "./guided-wizard";
import { PendingPromptBanner } from "./pending-prompt-banner";
import { PromptSandbox } from "@/components/prompt-sandbox";
import { PENDING_TEMPLATE_KEY } from "@/lib/constants";

export function PromptEditorView({ instanceId }: { instanceId: string }) {
  const [pendingTemplate] = useState(() => {
    const raw = sessionStorage.getItem(PENDING_TEMPLATE_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(PENDING_TEMPLATE_KEY);
    return JSON.parse(raw) as { content: string; title: string };
  });
  const [current, setCurrent] = useState<PromptVersionDetail | null>(null);
  const [content, setContent] = useState(pendingTemplate?.content ?? "");
  const [changeNote, setChangeNote] = useState(pendingTemplate ? `Template: ${pendingTemplate.title}` : "");
  const [pendingSource, setPendingSource] = useState<"manual" | "template">(pendingTemplate ? "template" : "manual");
  const [loading, setLoading] = useState(!pendingTemplate);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const loadCurrentVersion = useCallback((id: string) => {
    setLoading(true);
    setLoadError(null);
    apiFetch<PromptVersionDetail[]>(`/instances/${id}/prompt-versions`)
      .then((versions) => {
        const latest = versions[0];
        if (!latest) {
          setCurrent(null);
          setContent("");
          return;
        }
        return apiFetch<PromptVersionDetail>(`/instances/${id}/prompt-versions/${latest.id}`).then(
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
    if (pendingTemplate) return;
    // Fetching on mount is a necessary Effect (react.dev/learn/you-might-not-need-an-effect
    // #fetching-data); loadCurrentVersion resets loading/error synchronously before the fetch
    // settles, which set-state-in-effect can't distinguish from a derived-state anti-pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadCurrentVersion(instanceId);
  }, [instanceId, loadCurrentVersion, pendingTemplate]);


  async function handleSave() {
    setSaving(true);
    setSaveStatus(null);
    try {
      const version = await apiFetch<PromptVersionDetail>(`/instances/${instanceId}/prompt-versions`, {
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Agente de IA</h1>
        <div className="flex items-center gap-2">
          <PromptSandbox instanceId={instanceId} promptContent={content} />
          <AiAssistPanel
            instanceId={instanceId}
            currentContent={content}
            onApplied={() => loadCurrentVersion(instanceId)}
          />
        </div>
      </div>
      {loading ? <LoadingState /> : null}
      {!loading && loadError ? (
        <ErrorState message={loadError} onRetry={() => loadCurrentVersion(instanceId)} />
      ) : null}
      {!loading && !loadError ? (
        <>
          <AiPipelinePreview />
          <PendingPromptBanner
            instanceId={instanceId}
            currentContent={current?.content ?? ""}
            onResolved={() => loadCurrentVersion(instanceId)}
          />
          <p className="text-sm text-muted-foreground">
            {current ? `Versao atual: ${current.version_number}` : "Nenhuma versao salva ainda."}
          </p>
          <GuidedWizard key={current?.id ?? "new"} initialContent={content} onAssembledChange={setContent} />
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

export default function PromptEditorPage() {
  const { instances, selectedId, error: instancesError, reload: reloadInstances } = useOwnInstances();

  if (instancesError) {
    return <ErrorState message={instancesError} onRetry={reloadInstances} />;
  }
  if (instances === null) {
    return <LoadingState />;
  }
  if (instances.length === 0 || !selectedId) {
    return <EmptyState title="Nenhuma instancia associada a sua conta ainda." icon={Server} />;
  }
  return <PromptEditorView key={selectedId} instanceId={selectedId} />;
}
