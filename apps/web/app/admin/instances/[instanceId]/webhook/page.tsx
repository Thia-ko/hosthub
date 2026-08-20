"use client";

import { WebhookInspector } from "@/components/n8n-bridge/webhook-inspector";
import { WebhookIntegrationDocs } from "@/components/n8n-bridge/webhook-integration-docs";
import { OutboundWebhooksPanel } from "@/components/n8n-bridge/outbound-webhooks-panel";
import { RegenerateWebhookTokenButton } from "@/components/n8n-bridge/regenerate-webhook-token-button";
import { ApiKeysPanel } from "@/components/n8n-bridge/api-keys-panel";
import { ExternalApiDocs } from "@/components/n8n-bridge/external-api-docs";
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
      <ExternalApiDocs />
      <ApiKeysPanel instanceId={instance.id} />
    </div>
  );
}
