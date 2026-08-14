"use client";

import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { MobileCard, MobileCardList, MobileCardRow } from "@/components/mobile-card";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { PromptTemplate } from "@/lib/types";
import { TemplateFormDialog } from "./template-form-dialog";
import { toast } from "sonner";

export default function AdminTemplatesView() {
  const {
    data: templates,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<PromptTemplate[]>("/prompt-templates"), []);

  async function handleDelete(template: PromptTemplate) {
    await apiFetch(`/prompt-templates/${template.id}`, { method: "DELETE" });
    toast.success(`Template "${template.title}" excluido.`);
    reload();
  }

  function DeleteButton({ template }: { template: PromptTemplate }) {
    return (
      <ConfirmDialog
        trigger={
          <Button variant="ghost" size="sm">
            Excluir
          </Button>
        }
        title="Excluir template"
        description={
          <>
            Excluir o template <strong>{template.title}</strong>? Essa acao nao pode ser desfeita.
          </>
        }
        confirmLabel="Excluir"
        destructive
        onConfirm={() => handleDelete(template)}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Templates de prompt</h1>
        <TemplateFormDialog trigger={<Button>Novo template</Button>} onSaved={reload} />
      </div>
      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && !error && templates && templates.length === 0 ? (
        <EmptyState title="Nenhum template cadastrado ainda." />
      ) : null}
      {!loading && !error && templates && templates.length > 0 ? (
        <>
          <MobileCardList>
            {templates.map((template) => (
              <MobileCard key={template.id}>
                <div className="flex items-center justify-between gap-2">
                  <p className="font-medium">
                    {template.icon_emoji} {template.title}
                  </p>
                </div>
                <MobileCardRow label="Nicho">{template.niche}</MobileCardRow>
                <p className="text-sm text-muted-foreground">{template.description}</p>
                <div className="flex justify-end gap-2 pt-1">
                  <TemplateFormDialog
                    template={template}
                    trigger={
                      <Button variant="outline" size="sm">
                        Editar
                      </Button>
                    }
                    onSaved={reload}
                  />
                  <DeleteButton template={template} />
                </div>
              </MobileCard>
            ))}
          </MobileCardList>
          <div className="hidden sm:block">
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
                    <TableCell className="max-w-xs truncate text-muted-foreground">
                      {template.description}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-2">
                        <TemplateFormDialog
                          template={template}
                          trigger={
                            <Button variant="outline" size="sm">
                              Editar
                            </Button>
                          }
                          onSaved={reload}
                        />
                        <DeleteButton template={template} />
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
