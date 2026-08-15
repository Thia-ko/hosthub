import type { Metadata } from "next";
import EquipePage from "./view";

export const metadata: Metadata = { title: "Equipe | Hosthub" };

export default function EquipeRoutePage() {
  return <EquipePage />;
}
