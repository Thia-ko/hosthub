"use client";

import { use as usePromise } from "react";
import { InstanceDashboard } from "@/components/instance-dashboard";

export default function AdminInstanceDashboardPage({ params }: { params: Promise<{ instanceId: string }> }) {
  const { instanceId } = usePromise(params);
  return <InstanceDashboard instanceId={instanceId} />;
}
