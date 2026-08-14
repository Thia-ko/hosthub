"use client";

import { ConversationView } from "@/components/conversation-view";
import { useInstanceDetail } from "@/lib/instance-detail-context";

export default function AdminInstanceConversationsPage() {
  const { instance } = useInstanceDetail();
  return <ConversationView instanceId={instance.id} />;
}
