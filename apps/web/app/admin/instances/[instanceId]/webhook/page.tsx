"use client";

import { useEffect, useState, use as usePromise } from "react";
import { WebhookInspector } from "@/components/webhook-inspector";
import { apiFetch } from "@/lib/api-client";
import type { InstanceDetail } from "@/lib/types";

export default function AdminInstanceWebhookPage({
  params,
}: {
  params: Promise<{ instanceId: string }>;
}) {
  const { instanceId } = usePromise(params);
  const [detail, setDetail] = useState<InstanceDetail | null>(null);

  useEffect(() => {
    apiFetch<InstanceDetail>(`/instances/${instanceId}`).then(setDetail);
  }, [instanceId]);

  if (!detail) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  const webhookUrl =
    typeof window !== "undefined" ? `${window.location.origin}/webhooks/${detail.webhook_token}` : "";

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Webhook - {detail.name}</h1>
      <WebhookInspector instanceId={detail.id} webhookUrl={webhookUrl} />
    </div>
  );
}
