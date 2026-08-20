"use client";

import { Server } from "lucide-react";
import { FilasWorkspace } from "@/components/inbox/filas-workspace";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { useOwnInstances } from "@/lib/instance-context";

export default function FilasView() {
  const { instances, selectedId, error, reload } = useOwnInstances();

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (instances === null) return <LoadingState />;

  if (instances.length === 0 || !selectedId) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Filas de Atendimento</h1>
        <EmptyState title="Nenhuma instancia associada a sua conta ainda." icon={Server} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Filas de Atendimento</h1>
      <FilasWorkspace instanceId={selectedId} conversationsHref="/app/conversations" />
    </div>
  );
}
