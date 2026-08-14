"use client";

import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FormStatus } from "@/components/state";
import { GENERIC_SAVE_ERROR_MESSAGE, apiFetch, errorMessage } from "@/lib/api-client";
import type { PromptTemplate } from "@/lib/types";

export function TemplateFormDialog({
  template,
  trigger,
  onSaved,
}: {
  template?: PromptTemplate;
  trigger: React.ReactNode;
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [niche, setNiche] = useState(template?.niche ?? "");
  const [title, setTitle] = useState(template?.title ?? "");
  const [description, setDescription] = useState(template?.description ?? "");
  const [iconEmoji, setIconEmoji] = useState(template?.icon_emoji ?? "");
  const [content, setContent] = useState(template?.content ?? "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setNiche(template?.niche ?? "");
    setTitle(template?.title ?? "");
    setDescription(template?.description ?? "");
    setIconEmoji(template?.icon_emoji ?? "");
    setContent(template?.content ?? "");
    setError(null);
  }, [open, template]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const body = JSON.stringify({ niche, title, description, icon_emoji: iconEmoji || null, content });
    try {
      if (template) {
        await apiFetch(`/prompt-templates/${template.id}`, { method: "PATCH", body });
      } else {
        await apiFetch("/prompt-templates", { method: "POST", body });
      }
      setOpen(false);
      toast.success(template ? "Template atualizado." : "Template criado.");
      onSaved();
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{template ? "Editar template" : "Novo template"}</DialogTitle>
        </DialogHeader>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="niche">Nicho</Label>
              <Input id="niche" required value={niche} onChange={(event) => setNiche(event.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="iconEmoji">Emoji</Label>
              <Input id="iconEmoji" value={iconEmoji} onChange={(event) => setIconEmoji(event.target.value)} />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="title">Titulo</Label>
            <Input id="title" required value={title} onChange={(event) => setTitle(event.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="description">Descricao</Label>
            <Input
              id="description"
              required
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="content">Conteudo do prompt</Label>
            <Textarea
              id="content"
              required
              className="min-h-48 font-mono text-sm"
              value={content}
              onChange={(event) => setContent(event.target.value)}
            />
          </div>
          {error ? <FormStatus tone="error">{error}</FormStatus> : null}
          <DialogFooter>
            <Button type="submit" disabled={saving}>
              {saving ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
