"use client";

import { WebhookInspector } from "@/components/webhook-inspector";
import { WebhookIntegrationDocs } from "@/components/webhook-integration-docs";
import { OutboundWebhooksPanel } from "@/components/outbound-webhooks-panel";
import { RegenerateWebhookTokenButton } from "@/components/regenerate-webhook-token-button";
import { useInstanceDetail } from "@/lib/instance-detail-context";

export default function AdminInstanceWebhookPage() {
  const { instance, reload } = useInstanceDetail();
  const webhookUrl =
    typeof window !== "undefined" ? `${window.location.origin}/webhooks/${instance.webhook_token}` : "";

  return (
    <div className="flex flex-col gap-4">
      <WebhookIntegrationDocs webhookUrl={webhookUrl} />
      <WebhookInspector
        instanceId={instance.id}
        webhookUrl={webhookUrl}
        headerAction={<RegenerateWebhookTokenButton instanceId={instance.id} onRegenerated={reload} />}
      />
      <OutboundWebhooksPanel instanceId={instance.id} />
    </div>
  );
}
