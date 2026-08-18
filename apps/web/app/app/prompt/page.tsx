import type { Metadata } from "next";
import PromptEditorView from "./view";

export const metadata: Metadata = { title: "Agente de IA | Hosthub" };

export default function PromptEditorPage() {
  return <PromptEditorView />;
}
