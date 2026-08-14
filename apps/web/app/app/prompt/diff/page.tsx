import type { Metadata } from "next";
import PromptDiffView from "./view";

export const metadata: Metadata = { title: "Diff de versoes | Hosthub" };

export default function PromptDiffPage() {
  return <PromptDiffView />;
}
