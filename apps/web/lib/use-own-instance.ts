"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import type { Instance } from "@/lib/types";

export function useOwnInstances() {
  const [instances, setInstances] = useState<Instance[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Instance[]>("/instances").then((data) => {
      setInstances(data);
      setSelectedId(data[0]?.id ?? null);
    });
  }, []);

  return { instances, selectedId, setSelectedId };
}
