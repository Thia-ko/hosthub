"use client";

import { useState } from "react";
import { History } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { DiffView } from "@/components/diff-view";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { apiFetch, errorMessage } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { PromptVersionDetail, PromptVersionDiffResponse, PromptVersionSource, PromptVersionSummary } from "@/lib/types";

const SOURCE_LABEL: Record<PromptVersionSource, string> = {
  manual: "Manual",
  ai_assist: "Assistente de IA",
  template: "Template",
  auto_generated: "Geracao automatica",
};

/** Discreet version control embedded in the prompt editor header. Replaces the old standalone
 * `/app/prompt/historico` table and `/app/prompt/diff` page: the version list, the diff between
 * two picked versions, and one-click revert all live in a single sheet, no route changes. */
export function VersionHistorySheet({
  instanceId,
  currentVersionNumber,
  refreshKey,
  onRestored,
}: {
  instanceId: string;
  currentVersionNumber: number | null;
  /** Bump this in the parent after every save so the list refetches. */
  refreshKey: number;
  onRestored: (version: PromptVersionDetail) => void;
}) {
  const [open, setOpen] = useState(false);
  const [compare, setCompare] = useState<string[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const {
    data: versions,
    error: listError,
    loading: listLoading,
    reload: reloadList,
  } = useAsyncData(
    () => (open ? apiFetch<PromptVersionSummary[]>(`/instances/${instanceId}/prompt-versions`) : Promise.resolve(null)),
    [open, instanceId, refreshKey]
  );

  const { data: diffData } = useAsyncData(
    () =>
      compare.length === 2
        ? apiFetch<PromptVersionDiffResponse>(
            `/instances/${instanceId}/prompt-versions/diff?from=${compare[0]}&to=${compare[1]}`
          )
        : Promise.resolve(null),
    [compare, instanceId]
  );

  function toggleCompare(id: string) {
    setCompare((prev) => {
      if (prev.includes(id)) return prev.filter((item) => item !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  }

  async function restore(version: PromptVersionSummary) {
    setBusyId(version.id);
    setRestoreError(null);
    try {
      const detail = await apiFetch<PromptVersionDetail>(`/instances/${instanceId}/prompt-versions/${version.id}`);
      const restored = await apiFetch<PromptVersionDetail>(`/instances/${instanceId}/prompt-versions`, {
        method: "POST",
        body: JSON.stringify({
          content: detail.content,
          source: "manual",
          change_note: `Restaurado da versao ${version.version_number}`,
        }),
      });
      onRestored(restored);
      setOpen(false);
    } catch (err) {
      setRestoreError(errorMessage(err, "Nao foi possivel restaurar esta versao."));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) {
          setCompare([]);
          setRestoreError(null);
        }
      }}
    >
      <SheetTrigger asChild>
        <Button variant="ghost" size="sm">
          <History className="size-4" />
          {currentVersionNumber ? `v${currentVersionNumber}` : "Historico"}
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Historico de versoes</SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-4 px-4 pb-4">
          <p className="text-xs text-muted-foreground">
            Marque duas versoes para comparar. Use &quot;Restaurar&quot; para criar uma nova versao a partir de uma
            antiga.
          </p>
          {listLoading ? <LoadingState /> : null}
          {!listLoading && listError ? <ErrorState message={listError} onRetry={reloadList} /> : null}
          {!listLoading && !listError && versions?.length === 0 ? (
            <EmptyState title="Nenhuma versao salva ainda." icon={History} />
          ) : null}
          {restoreError ? <FormStatus tone="error">{restoreError}</FormStatus> : null}
          {!listLoading && !listError && versions && versions.length > 0 ? (
            <ul className="flex flex-col divide-y">
              {versions.map((version) => (
                <li key={version.id} className="flex items-start gap-3 py-2.5">
                  <Checkbox
                    className="mt-0.5"
                    checked={compare.includes(version.id)}
                    onCheckedChange={() => toggleCompare(version.id)}
                    aria-label={`Comparar versao ${version.version_number}`}
                  />
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium">v{version.version_number}</span>
                      <Badge variant="outline" className="text-[10px] font-normal">
                        {SOURCE_LABEL[version.source]}
                      </Badge>
                      {version.version_number === currentVersionNumber ? (
                        <Badge className="text-[10px] font-normal">Atual</Badge>
                      ) : null}
                    </div>
                    <p className="truncate text-xs text-muted-foreground">{version.change_note ?? "-"}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {new Date(version.created_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                  {version.version_number !== currentVersionNumber ? (
                    <Button variant="ghost" size="sm" disabled={busyId === version.id} onClick={() => restore(version)}>
                      Restaurar
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
          {compare.length === 2 && diffData ? (
            <div className="flex flex-col gap-2">
              <p className="text-xs font-medium text-muted-foreground">
                Comparando v{diffData.from.version_number} -&gt; v{diffData.to.version_number}
              </p>
              <DiffView from={diffData.from.content} to={diffData.to.content} />
            </div>
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
