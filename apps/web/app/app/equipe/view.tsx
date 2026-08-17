"use client";

import { InstanceMembersPanel } from "@/components/instance-members-panel";
import { Server } from "lucide-react";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { useOwnInstances } from "@/lib/instance-context";

export function EquipeView({ instanceId }: { instanceId: string }) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Equipe</h1>
      <InstanceMembersPanel instanceId={instanceId} />
    </div>
  );
}

export default function EquipePage() {
  const { instances, selectedId, error: instancesError, reload: reloadInstances } = useOwnInstances();

  if (instancesError) {
    return <ErrorState message={instancesError} onRetry={reloadInstances} />;
  }
  if (instances === null) {
    return <LoadingState />;
  }
  if (instances.length === 0 || !selectedId) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Equipe</h1>
        <EmptyState title="Nenhuma instancia associada a sua conta ainda." icon={Server} />
      </div>
    );
  }
  return <EquipeView key={selectedId} instanceId={selectedId} />;
}
