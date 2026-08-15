"use client";

import { use as usePromise } from "react";
import { PromptHistoryView } from "@/app/app/prompt/historico/view";

export default function AdminInstancePromptHistoryPage({
  params,
}: {
  params: Promise<{ instanceId: string }>;
}) {
  const { instanceId } = usePromise(params);
  return <PromptHistoryView instanceId={instanceId} basePath={`/admin/instances/${instanceId}/prompt`} />;
}
