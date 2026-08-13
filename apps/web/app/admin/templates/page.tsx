"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiFetch } from "@/lib/api-client";
import type { PromptTemplate } from "@/lib/types";
import { TemplateFormDialog } from "./template-form-dialog";

export default function AdminTemplatesPage() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);

  const load = useCallback(() => {
    apiFetch<PromptTemplate[]>("/prompt-templates").then(setTemplates);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(template: PromptTemplate) {
    if (!confirm(`Excluir o template "${template.title}"?`)) return;
    await apiFetch(`/prompt-templates/${template.id}`, { method: "DELETE" });
    load();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Templates de prompt</h1>
        <TemplateFormDialog trigger={<Button>Novo template</Button>} onSaved={load} />
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nicho</TableHead>
            <TableHead>Titulo</TableHead>
            <TableHead>Descricao</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {templates.map((template) => (
            <TableRow key={template.id}>
              <TableCell>{template.niche}</TableCell>
              <TableCell>
                {template.icon_emoji} {template.title}
              </TableCell>
              <TableCell className="text-muted-foreground">{template.description}</TableCell>
              <TableCell>
                <div className="flex justify-end gap-2">
                  <TemplateFormDialog
                    template={template}
                    trigger={
                      <Button variant="outline" size="sm">
                        Editar
                      </Button>
                    }
                    onSaved={load}
                  />
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(template)}>
                    Excluir
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
          {templates.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground">
                Nenhum template cadastrado ainda.
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}
