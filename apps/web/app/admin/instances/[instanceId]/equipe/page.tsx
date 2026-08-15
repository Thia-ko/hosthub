"use client";

import { use as usePromise } from "react";
import { EquipeView } from "@/app/app/equipe/view";

export default function AdminInstanceEquipePage({ params }: { params: Promise<{ instanceId: string }> }) {
  const { instanceId } = usePromise(params);
  return <EquipeView instanceId={instanceId} />;
}
