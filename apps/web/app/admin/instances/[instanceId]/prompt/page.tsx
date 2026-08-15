"use client";

import { use as usePromise } from "react";
import { PromptEditorView } from "@/app/app/prompt/view";

export default function AdminInstancePromptPage({ params }: { params: Promise<{ instanceId: string }> }) {
  const { instanceId } = usePromise(params);
  return <PromptEditorView instanceId={instanceId} />;
}
