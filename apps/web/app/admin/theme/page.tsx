import type { Metadata } from "next";
import AdminThemeView from "./view";

export const metadata: Metadata = { title: "Tema | Hosthub" };

export default function AdminThemePage() {
  return <AdminThemeView />;
}
