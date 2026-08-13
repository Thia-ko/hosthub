"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch, ApiError } from "@/lib/api-client";
import { useOwnInstances } from "@/lib/use-own-instance";
import type { PromptVersionDetail } from "@/lib/types";
import { InstanceSwitcher } from "./instance-switcher";

export default function PromptEditorPage() {
  const { instances, selectedId, setSelectedId } = useOwnInstances();
  const [current, setCurrent] = useState<PromptVersionDetail | null>(null);
  const [content, setContent] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId) return;
    apiFetch<PromptVersionDetail[]>(`/instances/${selectedId}/prompt-versions`).then((versions) => {
      const latest = versions[0];
      if (!latest) {
        setCurrent(null);
        setContent("");
        return;
      }
      apiFetch<PromptVersionDetail>(`/instances/${selectedId}/prompt-versions/${latest.id}`).then((detail) => {
        setCurrent(detail);
        setContent(detail.content);
      });
    });
  }, [selectedId]);

  async function handleSave() {
    if (!selectedId) return;
    setSaving(true);
    setMessage(null);
    try {
      const version = await apiFetch<PromptVersionDetail>(`/instances/${selectedId}/prompt-versions`, {
        method: "POST",
        body: JSON.stringify({ content, change_note: changeNote || null }),
      });
      setCurrent(version);
      setChangeNote("");
      setMessage(`Versao ${version.version_number} salva.`);
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Nao foi possivel salvar");
    } finally {
      setSaving(false);
    }
  }

  if (instances === null) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  if (instances.length === 0) {
    return <p className="text-sm text-muted-foreground">Nenhuma instancia associada a sua conta ainda.</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Prompt da IA</h1>
        <div className="flex items-center gap-3">
          {selectedId ? (
            <Link className="text-sm text-muted-foreground hover:underline" href="/app/prompt/historico">
              Ver historico
            </Link>
          ) : null}
          <InstanceSwitcher instances={instances} selectedId={selectedId ?? ""} onChange={setSelectedId} />
        </div>
      </div>
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
      {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
      <Button onClick={handleSave} disabled={saving || !content} className="w-fit">
        {saving ? "Salvando..." : "Salvar nova versao"}
      </Button>
    </div>
  );
}
