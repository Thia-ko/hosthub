"use client";

import { Server } from "lucide-react";
import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { MobileCard, MobileCardList, MobileCardRow } from "@/components/mobile-card";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { Instance } from "@/lib/types";
import { NewInstanceDialog } from "./new-instance-dialog";
import { StatusBadge } from "./status-badge";

export default function AdminInstancesView() {
  const { data: instances, error, loading, reload } = useAsyncData(() => apiFetch<Instance[]>("/instances"), []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Instancias</h1>
        <NewInstanceDialog onCreated={reload} />
      </div>
      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && !error && instances && instances.length === 0 ? (
        <EmptyState title="Nenhuma instancia criada ainda." icon={Server} />
      ) : null}
      {!loading && !error && instances && instances.length > 0 ? (
        <>
          <MobileCardList>
            {instances.map((instance) => (
              <MobileCard key={instance.id}>
                <Link className="font-medium hover:underline" href={`/admin/instances/${instance.id}`}>
                  {instance.name}
                </Link>
                <MobileCardRow label="Cliente">{instance.owner_email}</MobileCardRow>
                <MobileCardRow label="Status">
                  <StatusBadge status={instance.status} />
                </MobileCardRow>
                <MobileCardRow label="Criada em">
                  {new Date(instance.created_at).toLocaleDateString("pt-BR")}
                </MobileCardRow>
              </MobileCard>
            ))}
          </MobileCardList>
          <div className="hidden sm:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Criada em</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {instances.map((instance) => (
                  <TableRow key={instance.id}>
                    <TableCell>
                      <Link className="font-medium hover:underline" href={`/admin/instances/${instance.id}`}>
                        {instance.name}
                      </Link>
                    </TableCell>
                    <TableCell>{instance.owner_email}</TableCell>
                    <TableCell>
                      <StatusBadge status={instance.status} />
                    </TableCell>
                    <TableCell>{new Date(instance.created_at).toLocaleDateString("pt-BR")}</TableCell>
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
