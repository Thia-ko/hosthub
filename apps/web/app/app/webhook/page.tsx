import type { Metadata } from "next";
import WebhookView from "./view";

export const metadata: Metadata = { title: "Webhook | Hosthub" };

export default function WebhookPage() {
  return <WebhookView />;
}
