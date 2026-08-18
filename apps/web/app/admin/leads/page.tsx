import type { Metadata } from "next";
import AdminLeadsView from "./view";

export const metadata: Metadata = { title: "Leads da demo | Hosthub" };

export default function AdminLeadsPage() {
  return <AdminLeadsView />;
}
