import type { Metadata } from "next";
import CampaignsPage from "./view";

export const metadata: Metadata = { title: "Campanhas | Hosthub" };

export default function CampaignsRoutePage() {
  return <CampaignsPage />;
}
