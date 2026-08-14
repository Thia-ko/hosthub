import type { Metadata } from "next";
import AdminAiSettingsView from "./view";

export const metadata: Metadata = { title: "IA | Hosthub" };

export default function AdminAiSettingsPage() {
  return <AdminAiSettingsView />;
}
