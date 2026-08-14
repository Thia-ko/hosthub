import type { Metadata } from "next";
import PromptEditorView from "./view";

export const metadata: Metadata = { title: "Prompt da IA | Hosthub" };

export default function PromptEditorPage() {
  return <PromptEditorView />;
}
