import type { Metadata } from "next";
import ClientHomeView from "./view";

export const metadata: Metadata = { title: "Dashboard | Hosthub" };

export default function ClientHomePage() {
  return <ClientHomeView />;
}
