"use client";

import { WebhookInspector } from "@/components/webhook-inspector";
import { Server } from "lucide-react";
import { OutboundWebhooksPanel } from "@/components/outbound-webhooks-panel";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { apiFetch } from "@/lib/api-client";
import { useOwnInstances } from "@/lib/instance-context";
import { useAsyncData } from "@/lib/use-async-data";
import type { InstanceDetail } from "@/lib/types";

export default function WebhookView() {
  const { instances, selectedId, error: instancesError, reload: reloadInstances } = useOwnInstances();
  const {
    data: detail,
    error: detailError,
    loading: detailLoading,
    reload: reloadDetail,
  } = useAsyncData(
    () => (selectedId ? apiFetch<InstanceDetail>(`/instances/${selectedId}`) : Promise.resolve(null)),
    [selectedId]
  );

  if (instancesError) {
    return <ErrorState message={instancesError} onRetry={reloadInstances} />;
  }

  if (instances === null) {
    return <LoadingState />;
  }

  if (instances.length === 0 || !selectedId) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Webhook</h1>
        <EmptyState title="Nenhuma instancia associada a sua conta ainda." icon={Server} />
      </div>
    );
  }

  if (detailLoading) return <LoadingState />;
  if (detailError) return <ErrorState message={detailError} onRetry={reloadDetail} />;
  if (!detail) return null;

  const webhookUrl =
    typeof window !== "undefined" ? `${window.location.origin}/webhooks/${detail.webhook_token}` : "";

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Webhook</h1>
      <WebhookInspector instanceId={detail.id} webhookUrl={webhookUrl} />
      <OutboundWebhooksPanel instanceId={detail.id} />
    </div>
  );
}
