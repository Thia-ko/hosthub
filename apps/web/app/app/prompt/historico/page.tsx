import type { Metadata } from "next";
import PromptHistoryView from "./view";

export const metadata: Metadata = { title: "Historico de versoes | Hosthub" };

export default function PromptHistoryPage() {
  return <PromptHistoryView />;
}
