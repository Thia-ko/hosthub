"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { InstanceDetail } from "@/lib/types";

interface InstanceDetailContextValue {
  instance: InstanceDetail;
  reload: () => void;
}

const InstanceDetailContext = createContext<InstanceDetailContextValue | null>(null);

/** Shares the already-fetched instance across the Geral/Dashboard/Webhook admin tabs. */
export function InstanceDetailProvider({
  instance,
  reload,
  children,
}: {
  instance: InstanceDetail;
  reload: () => void;
  children: ReactNode;
}) {
  return <InstanceDetailContext.Provider value={{ instance, reload }}>{children}</InstanceDetailContext.Provider>;
}

export function useInstanceDetail() {
  const ctx = useContext(InstanceDetailContext);
  if (!ctx) throw new Error("useInstanceDetail must be used within InstanceDetailProvider");
  return ctx;
}
