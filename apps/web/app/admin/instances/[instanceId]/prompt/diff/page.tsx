import type { Metadata } from "next";
import PromptDiffView from "@/app/app/prompt/diff/view";

export const metadata: Metadata = { title: "Diff de versoes | Hosthub" };

export default function AdminPromptDiffPage() {
  return <PromptDiffView />;
}
