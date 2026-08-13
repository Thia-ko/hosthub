"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiFetch } from "@/lib/api-client";
import type { Instance } from "@/lib/types";
import { NewInstanceDialog } from "./new-instance-dialog";
import { StatusBadge } from "./status-badge";

export default function AdminInstancesPage() {
  const [instances, setInstances] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const data = await apiFetch<Instance[]>("/instances");
    setInstances(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Instancias</h1>
        <NewInstanceDialog onCreated={load} />
      </div>
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
          {!loading && instances.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                Nenhuma instancia criada ainda.
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}
