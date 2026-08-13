"use client";

import { useEffect, useState } from "react";
import { WebhookInspector } from "@/components/webhook-inspector";
import { apiFetch } from "@/lib/api-client";
import { useOwnInstances } from "@/lib/use-own-instance";
import type { InstanceDetail } from "@/lib/types";

export default function WebhookPage() {
  const { instances, selectedId } = useOwnInstances();
  const [detail, setDetail] = useState<InstanceDetail | null>(null);

  useEffect(() => {
    if (!selectedId) return;
    apiFetch<InstanceDetail>(`/instances/${selectedId}`).then(setDetail);
  }, [selectedId]);

  if (instances === null) {
    return <p className="text-sm text-muted-foreground">Carregando...</p>;
  }

  if (instances.length === 0 || !detail) {
    return <p className="text-sm text-muted-foreground">Nenhuma instancia associada a sua conta ainda.</p>;
  }

  const webhookUrl =
    typeof window !== "undefined" ? `${window.location.origin}/webhooks/${detail.webhook_token}` : "";

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Webhook</h1>
      <WebhookInspector instanceId={detail.id} webhookUrl={webhookUrl} />
    </div>
  );
}
