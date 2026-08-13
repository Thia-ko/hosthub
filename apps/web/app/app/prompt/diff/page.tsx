"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { diffLines, type Change } from "diff";
import { apiFetch } from "@/lib/api-client";
import type { PromptVersionDiffResponse } from "@/lib/types";

function DiffLine({ change, index }: { change: Change; index: number }) {
  const prefix = change.added ? "+" : change.removed ? "-" : " ";
  const background = change.added ? "bg-emerald-50 text-emerald-900" : change.removed ? "bg-red-50 text-red-900" : "";
  const lines = change.value.endsWith("\n")
    ? change.value.slice(0, -1).split("\n")
    : change.value.split("\n");
  return (
    <>
      {lines.map((line, lineIndex) => (
        <div key={`${index}-${lineIndex}`} className={`whitespace-pre-wrap px-3 py-0.5 font-mono text-xs ${background}`}>
          {prefix} {line}
        </div>
      ))}
    </>
  );
}

function PromptDiffContent() {
  const searchParams = useSearchParams();
  const instanceId = searchParams.get("instance");
  const from = searchParams.get("from");
  const to = searchParams.get("to");
  const [diffData, setDiffData] = useState<PromptVersionDiffResponse | null>(null);

  useEffect(() => {
    if (!instanceId || !from || !to) return;
    apiFetch<PromptVersionDiffResponse>(
      `/instances/${instanceId}/prompt-versions/diff?from=${from}&to=${to}`
    ).then(setDiffData);
  }, [instanceId, from, to]);

  if (!instanceId || !from || !to) {
    return <p className="text-sm text-muted-foreground">Selecione duas versoes no historico para comparar.</p>;
  }

  if (!diffData) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  const changes = diffLines(diffData.from.content, diffData.to.content);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">
        Diff: versao {diffData.from.version_number} -&gt; versao {diffData.to.version_number}
      </h1>
      <div className="overflow-hidden rounded-md border">
        {changes.map((change, index) => (
          <DiffLine key={index} change={change} index={index} />
        ))}
      </div>
    </div>
  );
}

export default function PromptDiffPage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Carregando...</p>}>
      <PromptDiffContent />
    </Suspense>
  );
}
