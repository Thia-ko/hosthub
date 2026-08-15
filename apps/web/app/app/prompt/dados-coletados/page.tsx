import type { Metadata } from "next";
import DadosColetadosView from "./view";

export const metadata: Metadata = { title: "Dados coletados | Hosthub" };

export default function DadosColetadosPage() {
  return <DadosColetadosView />;
}
