import type { Metadata } from "next";
import AdminInstancesView from "./view";

export const metadata: Metadata = { title: "Instancias | Hosthub" };

export default function AdminInstancesPage() {
  return <AdminInstancesView />;
}
