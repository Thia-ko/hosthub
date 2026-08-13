"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiFetch } from "@/lib/api-client";
import { useOwnInstances } from "@/lib/use-own-instance";
import type { PromptVersionSource, PromptVersionSummary } from "@/lib/types";
import { InstanceSwitcher } from "../instance-switcher";

const SOURCE_LABEL: Record<PromptVersionSource, string> = {
  manual: "Manual",
  ai_assist: "Assistente de IA",
  template: "Template",
};

export default function PromptHistoryPage() {
  const router = useRouter();
  const { instances, selectedId, setSelectedId } = useOwnInstances();
  const [versions, setVersions] = useState<PromptVersionSummary[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    if (!selectedId) return;
    apiFetch<PromptVersionSummary[]>(`/instances/${selectedId}/prompt-versions`).then(setVersions);
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
    if (selected.length !== 2 || !selectedId) return;
    const [a, b] = selected;
    const aVersion = versions.find((v) => v.id === a);
    const bVersion = versions.find((v) => v.id === b);
    if (!aVersion || !bVersion) return;
    const [from, to] = aVersion.version_number < bVersion.version_number ? [a, b] : [b, a];
    router.push(`/app/prompt/diff?instance=${selectedId}&from=${from}&to=${to}`);
  }

  if (instances === null) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Historico de versoes</h1>
        <div className="flex items-center gap-3">
          <Button onClick={openDiff} disabled={selected.length !== 2} variant="outline">
            Ver diff
          </Button>
          {instances.length > 0 ? (
            <InstanceSwitcher instances={instances} selectedId={selectedId ?? ""} onChange={setSelectedId} />
          ) : null}
        </div>
      </div>
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
                <Checkbox
                  checked={selected.includes(version.id)}
                  onCheckedChange={() => toggle(version.id)}
                />
              </TableCell>
              <TableCell>{version.version_number}</TableCell>
              <TableCell>
                <Badge variant="secondary">{SOURCE_LABEL[version.source]}</Badge>
              </TableCell>
              <TableCell>{version.change_note ?? "-"}</TableCell>
              <TableCell>{new Date(version.created_at).toLocaleString("pt-BR")}</TableCell>
            </TableRow>
          ))}
          {versions.length === 0 ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground">
                Nenhuma versao salva ainda.
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}
