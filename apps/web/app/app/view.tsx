"use client";

import { Server } from "lucide-react";
import { InstanceDashboard } from "@/components/instance-dashboard";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { useOwnInstances } from "@/lib/instance-context";

export default function ClientHomeView() {
  const { instances, selectedId, error, reload } = useOwnInstances();

  if (error) {
    return <ErrorState message={error} onRetry={reload} />;
  }

  if (instances === null) {
    return <LoadingState />;
  }

  if (instances.length === 0 || !selectedId) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Sua IA</h1>
        <EmptyState
          title="Nenhuma instancia associada a sua conta ainda."
          description="Fale com o administrador para vincular sua conta a uma instancia."
          icon={Server}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Sua IA</h1>
      <InstanceDashboard instanceId={selectedId} promptHref="/app/prompt" />
    </div>
  );
}
