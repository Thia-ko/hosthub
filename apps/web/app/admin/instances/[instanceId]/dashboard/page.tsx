"use client";

import { use as usePromise } from "react";
import { InstanceDashboard } from "@/components/instance-dashboard";

export default function AdminInstanceDashboardPage({
  params,
}: {
  params: Promise<{ instanceId: string }>;
}) {
  const { instanceId } = usePromise(params);

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <InstanceDashboard instanceId={instanceId} />
    </div>
  );
}
