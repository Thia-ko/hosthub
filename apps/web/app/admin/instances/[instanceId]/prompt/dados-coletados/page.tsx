"use client";

import { use as usePromise } from "react";
import { DadosColetadosView } from "@/app/app/prompt/dados-coletados/view";

export default function AdminInstanceDadosColetadosPage({
  params,
}: {
  params: Promise<{ instanceId: string }>;
}) {
  const { instanceId } = usePromise(params);
  return <DadosColetadosView instanceId={instanceId} />;
}
