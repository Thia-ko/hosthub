import type { Metadata } from "next";
import ConexaoView from "./view";

export const metadata: Metadata = { title: "Conexao | Hosthub" };

export default function ConexaoPage() {
  return <ConexaoView />;
}
