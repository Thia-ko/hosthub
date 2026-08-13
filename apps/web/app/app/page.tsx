"use client";

import { InstanceDashboard } from "@/components/instance-dashboard";
import { useOwnInstances } from "@/lib/use-own-instance";
import { InstanceSwitcher } from "@/components/instance-switcher";

export default function ClientHomePage() {
  const { instances, selectedId, setSelectedId } = useOwnInstances();

  if (instances === null) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  if (instances.length === 0 || !selectedId) {
    return (
      <div>
        <h1 className="text-xl font-semibold">Sua IA</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Nenhuma instancia associada a sua conta ainda. Fale com o administrador.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Sua IA</h1>
        <InstanceSwitcher instances={instances} selectedId={selectedId} onChange={setSelectedId} />
      </div>
      <InstanceDashboard instanceId={selectedId} />
    </div>
  );
}
