"use client";

import { useEffect, useRef, useState, type ChangeEvent, type ComponentType } from "react";
import { toast } from "sonner";
import { FileText, Image as ImageIcon, Music, Paperclip, Trash2, Upload, Video } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { ApiError, apiFetch, errorMessage, GENERIC_SAVE_ERROR_MESSAGE } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { KnowledgeFile, KnowledgeFileUsageMode } from "@/lib/types";

const KIND_ICON: Record<KnowledgeFile["kind"], ComponentType<{ className?: string }>> = {
  text: FileText,
  image: ImageIcon,
  audio: Music,
  video: Video,
};

const USAGE_MODE_LABEL: Record<KnowledgeFileUsageMode, string> = {
  auto: "Automatico",
  manual: "Manual",
  disabled: "Desativado",
};

const ACCEPTED_TYPES = "text/plain,text/markdown,text/csv,image/*,audio/*,video/*";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** apiFetch always sets Content-Type: application/json, which breaks multipart uploads - use a
 * raw fetch for this one call instead, mirroring apiFetch's error shape for consistent toasts. */
async function uploadKnowledgeFile(instanceId: string, file: File): Promise<KnowledgeFile> {
  const formData = new FormData();
  formData.append("upload", file);
  const response = await fetch(`/api/v1/instances/${instanceId}/knowledge-files`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!response.ok) {
    throw new ApiError(response.status, body);
  }
  return body as KnowledgeFile;
}

function KnowledgeFileRow({
  item,
  onUpdate,
  onDelete,
}: {
  item: KnowledgeFile;
  onUpdate: (id: string, payload: Partial<Pick<KnowledgeFile, "usage_mode" | "include_next" | "content_text">>) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const Icon = KIND_ICON[item.kind];
  const [contentText, setContentText] = useState(item.content_text ?? "");
  const [savingText, setSavingText] = useState(false);

  async function handleTextBlur() {
    if (contentText === (item.content_text ?? "")) return;
    setSavingText(true);
    try {
      await onUpdate(item.id, { content_text: contentText });
      toast.success("Descricao atualizada.");
    } catch (err) {
      toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSavingText(false);
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Icon className="size-4 shrink-0 text-muted-foreground" />
          <span className="min-w-0 truncate font-medium">{item.filename}</span>
          <span className="shrink-0 text-xs text-muted-foreground">{formatSize(item.size_bytes)}</span>
          {item.status === "processing_failed" ? <Badge variant="destructive">Falha ao processar</Badge> : null}
        </div>
        <ConfirmDialog
          trigger={
            <Button size="icon" variant="ghost" className="size-7 shrink-0">
              <Trash2 className="size-3.5" />
            </Button>
          }
          title="Remover arquivo"
          description={`Remover "${item.filename}" da base de conhecimento?`}
          confirmLabel="Remover"
          destructive
          onConfirm={() => onDelete(item.id)}
        />
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs text-muted-foreground">Uso no prompt</Label>
          <Select
            value={item.usage_mode}
            onValueChange={async (value) => {
              try {
                await onUpdate(item.id, { usage_mode: value as KnowledgeFileUsageMode });
                toast.success("Modo de uso atualizado.");
              } catch (err) {
                toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
              }
            }}
          >
            <SelectTrigger className="h-8 w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.entries(USAGE_MODE_LABEL) as [KnowledgeFileUsageMode, string][]).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {item.usage_mode === "manual" ? (
          <div className="flex items-center gap-2 pt-4">
            <Checkbox
              id={`include-next-${item.id}`}
              checked={item.include_next}
              onCheckedChange={async (checked) => {
                try {
                  await onUpdate(item.id, { include_next: checked === true });
                  toast.success("Preferencia atualizada.");
                } catch (err) {
                  toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
                }
              }}
            />
            <Label htmlFor={`include-next-${item.id}`}>Usar na proxima geracao</Label>
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label className="text-xs text-muted-foreground">Descricao/transcricao</Label>
        <Textarea
          value={contentText}
          onChange={(event) => setContentText(event.target.value)}
          onBlur={handleTextBlur}
          placeholder={item.kind === "video" ? "Descreva o conteudo deste video..." : "Sem conteudo extraido ainda."}
          disabled={savingText}
          className="min-h-20"
        />
      </div>
    </div>
  );
}

export function KnowledgeFileManager({
  instanceId,
  onCountChange,
}: {
  instanceId: string;
  onCountChange?: (count: number) => void;
}) {
  const { data: files, error, loading, reload } = useAsyncData(
    () => apiFetch<KnowledgeFile[]>(`/instances/${instanceId}/knowledge-files`),
    [instanceId]
  );
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    onCountChange?.(files?.length ?? 0);
  }, [files, onCountChange]);

  async function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setUploading(true);
    try {
      await uploadKnowledgeFile(instanceId, file);
      toast.success("Arquivo enviado com sucesso.");
      reload();
    } catch (err) {
      toast.error(errorMessage(err, "Nao foi possivel enviar o arquivo."));
    } finally {
      setUploading(false);
    }
  }

  async function handleUpdate(
    id: string,
    payload: Partial<Pick<KnowledgeFile, "usage_mode" | "include_next" | "content_text">>
  ) {
    await apiFetch(`/instances/${instanceId}/knowledge-files/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    reload();
  }

  async function handleDelete(id: string) {
    try {
      await apiFetch(`/instances/${instanceId}/knowledge-files/${id}`, { method: "DELETE" });
      toast.success("Arquivo removido.");
      reload();
    } catch (err) {
      toast.error(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        Envie arquivos de texto, imagem, audio ou video para servirem de material de referencia para o agente
        de IA. Imagens e audios sao descritos/transcritos automaticamente; videos precisam de uma descricao
        manual.
      </p>
      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={handleFileChange}
        />
        <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
          <Upload className="size-3.5" />
          {uploading ? "Enviando..." : "Enviar arquivo"}
        </Button>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && !error && (files ?? []).length === 0 ? (
        <EmptyState
          icon={Paperclip}
          title="Nenhum arquivo enviado"
          description="Envie arquivos de texto, imagem, audio ou video para alimentar o agente de IA."
          bordered={false}
        />
      ) : null}
      {(files ?? []).map((item) => (
        <KnowledgeFileRow key={item.id} item={item} onUpdate={handleUpdate} onDelete={handleDelete} />
      ))}
    </div>
  );
}
