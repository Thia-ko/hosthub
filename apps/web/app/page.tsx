import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/api-server";
import LandingView from "./landing-view";

export const metadata: Metadata = {
  title: "Hosthub — Atendimento no WhatsApp com IA",
  description:
    "Conecte um agente de IA treinado no seu negocio ao WhatsApp: responde clientes 24/7 e sabe quando chamar um humano.",
};

export default async function RootPage() {
  const user = await getCurrentUser();
  if (user) redirect(user.role === "admin" ? "/admin" : "/app");
  return <LandingView />;
}
