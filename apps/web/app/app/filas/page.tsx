import type { Metadata } from "next";
import FilasView from "./view";

export const metadata: Metadata = { title: "Filas de Atendimento | Hosthub" };

export default function FilasPage() {
  return <FilasView />;
}
