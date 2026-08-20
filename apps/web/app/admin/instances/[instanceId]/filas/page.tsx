"use client";

import { FilasWorkspace } from "@/components/inbox/filas-workspace";
import { useInstanceDetail } from "@/lib/instance-detail-context";

export default function AdminInstanceFilasPage() {
  const { instance } = useInstanceDetail();
  return <FilasWorkspace instanceId={instance.id} conversationsHref={`/admin/instances/${instance.id}/conversations`} />;
}
