"use client";

import { use as usePromise } from "react";
import { WhatsAppConnectionView } from "@/app/app/conexao/view";

export default function AdminInstanceConexaoPage({ params }: { params: Promise<{ instanceId: string }> }) {
  const { instanceId } = usePromise(params);
  return <WhatsAppConnectionView instanceId={instanceId} />;
}
