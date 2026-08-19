import type { Metadata } from "next";
import ChatbotPage from "./view";

export const metadata: Metadata = { title: "Chatbot | Hosthub" };

export default function ChatbotRoutePage() {
  return <ChatbotPage />;
}
