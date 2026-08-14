"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import { DiffView } from "@/components/diff-view";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { useAsyncData } from "@/lib/use-async-data";
import type { PromptVersionDiffResponse } from "@/lib/types";

function PromptDiffContent() {
  const searchParams = useSearchParams();
  const instanceId = searchParams.get("instance");
  const from = searchParams.get("from");
  const to = searchParams.get("to");

  const { data: diffData, error, loading, reload } = useAsyncData(
    () =>
      instanceId && from && to
        ? apiFetch<PromptVersionDiffResponse>(`/instances/${instanceId}/prompt-versions/diff?from=${from}&to=${to}`)
        : Promise.resolve(null),
    [instanceId, from, to]
  );

  if (!instanceId || !from || !to) {
    return <EmptyState title="Selecione duas versoes no historico para comparar." />;
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!diffData) return null;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">
        Diff: versao {diffData.from.version_number} -&gt; versao {diffData.to.version_number}
      </h1>
      <DiffView from={diffData.from.content} to={diffData.to.content} />
    </div>
  );
}

export default function PromptDiffView() {
  return (
    <Suspense fallback={<LoadingState />}>
      <PromptDiffContent />
    </Suspense>
  );
}
