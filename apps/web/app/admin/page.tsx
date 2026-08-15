import type { Metadata } from "next";
import AdminHomeView from "./view";

export const metadata: Metadata = { title: "Visao geral | Hosthub" };

export default function AdminHomePage() {
  return <AdminHomeView />;
}
