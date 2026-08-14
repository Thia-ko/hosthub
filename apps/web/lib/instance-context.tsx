"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { apiFetch, errorMessage } from "@/lib/api-client";
import type { Instance } from "@/lib/types";

interface OwnInstanceContextValue {
  instances: Instance[] | null;
  selectedId: string | null;
  setSelectedId: (id: string) => void;
  error: string | null;
  reload: () => void;
}

const OwnInstanceContext = createContext<OwnInstanceContextValue | null>(null);

/**
 * Loads the client's own instances once and shares the selected instance across every
 * page under /app, so switching instances in the shell header persists across navigation.
 */
export function OwnInstanceProvider({ children }: { children: ReactNode }) {
  const [instances, setInstances] = useState<Instance[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    apiFetch<Instance[]>("/instances")
      .then((data) => {
        setInstances(data);
        setSelectedId((current) => current ?? data[0]?.id ?? null);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(errorMessage(err, "Nao foi possivel carregar suas instancias."));
      });
  }, [tick]);

  return (
    <OwnInstanceContext.Provider
      value={{ instances, selectedId, setSelectedId, error, reload: () => setTick((current) => current + 1) }}
    >
      {children}
    </OwnInstanceContext.Provider>
  );
}

export function useOwnInstances() {
  const ctx = useContext(OwnInstanceContext);
  if (!ctx) throw new Error("useOwnInstances must be used within OwnInstanceProvider");
  return ctx;
}
