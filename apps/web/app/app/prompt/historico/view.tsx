"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { MobileCard, MobileCardList, MobileCardRow } from "@/components/mobile-card";
import { apiFetch } from "@/lib/api-client";
import { useOwnInstances } from "@/lib/instance-context";
import { useAsyncData } from "@/lib/use-async-data";
import type { PromptVersionSource, PromptVersionSummary } from "@/lib/types";

const SOURCE_LABEL: Record<PromptVersionSource, string> = {
  manual: "Manual",
  ai_assist: "Assistente de IA",
  template: "Template",
  auto_generated: "Geracao automatica",
};

export default function PromptHistoryView() {
  const router = useRouter();
  const { instances, selectedId, error: instancesError, reload: reloadInstances } = useOwnInstances();
  const {
    data: versions,
    error: versionsError,
    loading: versionsLoading,
    reload: reloadVersions,
  } = useAsyncData(
    () =>
      selectedId
        ? apiFetch<PromptVersionSummary[]>(`/instances/${selectedId}/prompt-versions`)
        : Promise.resolve([]),
    [selectedId]
  );
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    setSelected([]);
  }, [selectedId]);

  function toggle(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((item) => item !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  }

  function openDiff() {
    if (selected.length !== 2 || !selectedId || !versions) return;
    const [a, b] = selected;
    const aVersion = versions.find((v) => v.id === a);
    const bVersion = versions.find((v) => v.id === b);
    if (!aVersion || !bVersion) return;
    const [from, to] = aVersion.version_number < bVersion.version_number ? [a, b] : [b, a];
    router.push(`/app/prompt/diff?instance=${selectedId}&from=${from}&to=${to}`);
  }

  if (instancesError) {
    return <ErrorState message={instancesError} onRetry={reloadInstances} />;
  }

  if (instances === null) {
    return <LoadingState />;
  }

  if (instances.length === 0 || !selectedId) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Historico de versoes</h1>
        <EmptyState title="Nenhuma instancia associada a sua conta ainda." />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Historico de versoes</h1>
        <Button onClick={openDiff} disabled={selected.length !== 2} variant="outline">
          Ver diff
        </Button>
      </div>
      {versionsLoading ? <LoadingState /> : null}
      {!versionsLoading && versionsError ? <ErrorState message={versionsError} onRetry={reloadVersions} /> : null}
      {!versionsLoading && !versionsError && versions && versions.length === 0 ? (
        <EmptyState title="Nenhuma versao salva ainda." />
      ) : null}
      {!versionsLoading && !versionsError && versions && versions.length > 0 ? (
        <>
          <MobileCardList>
            {versions.map((version) => (
              <MobileCard key={version.id}>
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium">Versao {version.version_number}</p>
                  <Checkbox checked={selected.includes(version.id)} onCheckedChange={() => toggle(version.id)} />
                </div>
                <MobileCardRow label="Origem">
                  <Badge variant="secondary">{SOURCE_LABEL[version.source]}</Badge>
                </MobileCardRow>
                <MobileCardRow label="Nota">{version.change_note ?? "-"}</MobileCardRow>
                <MobileCardRow label="Criada em">
                  {new Date(version.created_at).toLocaleString("pt-BR")}
                </MobileCardRow>
              </MobileCard>
            ))}
          </MobileCardList>
          <div className="hidden sm:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead />
                  <TableHead>Versao</TableHead>
                  <TableHead>Origem</TableHead>
                  <TableHead>Nota</TableHead>
                  <TableHead>Criada em</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.map((version) => (
                  <TableRow key={version.id}>
                    <TableCell>
                      <Checkbox checked={selected.includes(version.id)} onCheckedChange={() => toggle(version.id)} />
                    </TableCell>
                    <TableCell>{version.version_number}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">{SOURCE_LABEL[version.source]}</Badge>
                    </TableCell>
                    <TableCell>{version.change_note ?? "-"}</TableCell>
                    <TableCell>{new Date(version.created_at).toLocaleString("pt-BR")}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      ) : null}
    </div>
  );
}
