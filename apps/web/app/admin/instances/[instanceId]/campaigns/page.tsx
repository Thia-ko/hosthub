"use client";

import { use as usePromise } from "react";
import { CampaignsView } from "@/app/app/campaigns/view";

export default function AdminInstanceCampaignsPage({ params }: { params: Promise<{ instanceId: string }> }) {
  const { instanceId } = usePromise(params);
  return <CampaignsView instanceId={instanceId} />;
}
