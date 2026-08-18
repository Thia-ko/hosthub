"use client";

import { UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { MobileCard, MobileCardList, MobileCardRow } from "@/components/mobile-card";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { DemoLead } from "@/lib/types";

export default function AdminLeadsView() {
  const {
    data: leads,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<DemoLead[]>("/demo/leads"), []);

  async function toggleContacted(lead: DemoLead) {
    await apiFetch(`/demo/leads/${lead.id}`, {
      method: "PATCH",
      body: JSON.stringify({ contacted: !lead.contacted_at }),
    });
    reload();
  }

  function ContactedButton({ lead }: { lead: DemoLead }) {
    return (
      <Button size="sm" variant={lead.contacted_at ? "outline" : "default"} onClick={() => toggleContacted(lead)}>
        {lead.contacted_at ? "Contatado" : "Marcar como contatado"}
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Leads da demo</h1>
      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && !error && leads && leads.length === 0 ? (
        <EmptyState title="Nenhum lead da demo ainda." icon={UserPlus} />
      ) : null}
      {!loading && !error && leads && leads.length > 0 ? (
        <>
          <MobileCardList>
            {leads.map((lead) => (
              <MobileCard key={lead.id}>
                <p className="font-medium">{lead.name}</p>
                <MobileCardRow label="Contato">{lead.contact}</MobileCardRow>
                <MobileCardRow label="Negocio">{lead.business_name || "-"}</MobileCardRow>
                {lead.note ? <p className="text-sm text-muted-foreground">{lead.note}</p> : null}
                <MobileCardRow label="Criado em">
                  {new Date(lead.created_at).toLocaleString("pt-BR")}
                </MobileCardRow>
                <div className="flex justify-end pt-1">
                  <ContactedButton lead={lead} />
                </div>
              </MobileCard>
            ))}
          </MobileCardList>
          <div className="hidden sm:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Contato</TableHead>
                  <TableHead>Negocio</TableHead>
                  <TableHead>Nota</TableHead>
                  <TableHead>Criado em</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.map((lead) => (
                  <TableRow key={lead.id}>
                    <TableCell>{lead.name}</TableCell>
                    <TableCell>{lead.contact}</TableCell>
                    <TableCell>{lead.business_name || "-"}</TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">{lead.note || "-"}</TableCell>
                    <TableCell>{new Date(lead.created_at).toLocaleString("pt-BR")}</TableCell>
                    <TableCell>
                      <div className="flex justify-end">
                        <ContactedButton lead={lead} />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      ) : null}
    </div>
  );
}
