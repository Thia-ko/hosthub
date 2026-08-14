"use client";

import { InstanceSwitcher } from "@/components/instance-switcher";
import { useOwnInstances } from "@/lib/instance-context";

/** Renders the shell's top bar for /app; nothing to show below two instances, so it stays empty. */
export function InstanceSwitcherSlot() {
  const { instances, selectedId, setSelectedId } = useOwnInstances();
  if (!instances || instances.length < 2 || !selectedId) return null;
  return (
    <header className="flex items-center justify-end gap-3 border-b bg-background px-4 py-3 lg:px-6">
      <InstanceSwitcher instances={instances} selectedId={selectedId} onChange={setSelectedId} />
    </header>
  );
}
