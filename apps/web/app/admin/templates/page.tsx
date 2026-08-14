import type { Metadata } from "next";
import AdminTemplatesView from "./view";

export const metadata: Metadata = { title: "Templates de prompt | Hosthub" };

export default function AdminTemplatesPage() {
  return <AdminTemplatesView />;
}
