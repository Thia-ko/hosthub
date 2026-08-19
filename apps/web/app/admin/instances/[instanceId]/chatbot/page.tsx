"use client";

import { use as usePromise } from "react";
import { ChatbotView } from "@/app/app/chatbot/view";

export default function AdminInstanceChatbotPage({ params }: { params: Promise<{ instanceId: string }> }) {
  const { instanceId } = usePromise(params);
  return <ChatbotView instanceId={instanceId} />;
}
