import type { Metadata } from "next";
import ConversationsView from "./view";

export const metadata: Metadata = { title: "Conversas | Hosthub" };

export default function ConversationsPage() {
  return <ConversationsView />;
}
