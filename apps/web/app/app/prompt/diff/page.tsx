"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import { DiffView } from "@/components/diff-view";
import type { PromptVersionDiffResponse } from "@/lib/types";

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

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">
        Diff: versao {diffData.from.version_number} -&gt; versao {diffData.to.version_number}
      </h1>
      <DiffView from={diffData.from.content} to={diffData.to.content} />
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
