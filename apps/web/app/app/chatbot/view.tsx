"use client";

import { Server } from "lucide-react";
import { ChatbotTreeEditor } from "@/components/chatbot-tree-editor";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { useOwnInstances } from "@/lib/instance-context";

export function ChatbotView({ instanceId }: { instanceId: string }) {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Chatbot</h1>
      <ChatbotTreeEditor instanceId={instanceId} />
    </div>
  );
}

export default function ChatbotPage() {
  const { instances, selectedId, error: instancesError, reload: reloadInstances } = useOwnInstances();

  if (instancesError) {
    return <ErrorState message={instancesError} onRetry={reloadInstances} />;
  }
  if (instances === null) {
    return <LoadingState />;
  }
  if (instances.length === 0 || !selectedId) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Chatbot</h1>
        <EmptyState title="Nenhuma instancia associada a sua conta ainda." icon={Server} />
      </div>
    );
  }
  return <ChatbotView key={selectedId} instanceId={selectedId} />;
}
