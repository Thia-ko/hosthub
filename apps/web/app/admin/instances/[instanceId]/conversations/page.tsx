"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { ConversationView } from "@/components/inbox/conversation-view";
import { LoadingState } from "@/components/state";
import { useInstanceDetail } from "@/lib/instance-detail-context";

function AdminInstanceConversationsContent() {
  const { instance } = useInstanceDetail();
  const searchParams = useSearchParams();
  return <ConversationView instanceId={instance.id} initialSender={searchParams.get("sender")} />;
}

export default function AdminInstanceConversationsPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <AdminInstanceConversationsContent />
    </Suspense>
  );
}
