"use client";

import { useMemo, useState, type ComponentType } from "react";
import { toast } from "sonner";
import {
  Building2,
  ChevronDown,
  ChevronRight,
  HelpCircle,
  Pencil,
  Plus,
  ScrollText,
  ShoppingBag,
  Sparkles,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, FormStatus, LoadingState } from "@/components/state";
import { apiFetch, errorMessage, GENERIC_SAVE_ERROR_MESSAGE } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import { useOwnInstances } from "@/lib/instance-context";
import type { AttendantPattern, DataReadiness, ExtractedData, FaqItem, GeneratedPrompt } from "@/lib/types";

const CATEGORY_LABEL: Record<string, string> = {
  business_info: "Informacoes do negocio",
  products_services: "Produtos e servicos",
  policies: "Politicas",
};

const CATEGORY_ICON: Record<string, ComponentType<{ className?: string }>> = {
  business_info: Building2,
  products_services: ShoppingBag,
  policies: ScrollText,
};

function Section({
  title,
  icon: Icon,
  count,
  children,
  defaultOpen = true,
}: {
  title: string;
  icon: ComponentType<{ className?: string }>;
  count: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between rounded-t-lg p-4 text-left transition-colors hover:bg-muted/30"
      >
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" />
          <span className="text-sm font-semibold">{title}</span>
          <Badge variant="secondary" className="h-5 text-xs">
            {count}
          </Badge>
        </div>
        {open ? (
          <ChevronDown className="size-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 text-muted-foreground" />
        )}
      </button>
      {open ? <CardContent className="flex flex-col gap-2 px-4 pt-0 pb-4">{children}</CardContent> : null}
    </Card>
  );
}

function ExtractedRow({
  item,
  onSave,
  onDelete,
}: {
  item: ExtractedData;
  onSave: (id: string, value: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(item.value);
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!value.trim() || value === item.value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    await onSave(item.id, value.trim());
    setSaving(false);
    setEditing(false);
  }

  return (
    <div className="flex items-start justify-between gap-2 rounded-md border px-3 py-2 text-sm">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="font-medium">{item.key}</span>
        {editing ? (
          <Input value={value} onChange={(event) => setValue(event.target.value)} className="h-8" autoFocus />
        ) : (
          <span className="text-muted-foreground">{item.value}</span>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {editing ? (
          <>
            <Button size="icon" variant="ghost" className="size-7" onClick={save} disabled={saving}>
              <Pencil className="size-3.5" />
            </Button>
            <Button size="icon" variant="ghost" className="size-7" onClick={() => setEditing(false)}>
              <X className="size-3.5" />
            </Button>
          </>
        ) : (
          <>
            <Button size="icon" variant="ghost" className="size-7" onClick={() => setEditing(true)}>
              <Pencil className="size-3.5" />
            </Button>
            <ConfirmDialog
              trigger={
                <Button size="icon" variant="ghost" className="size-7">
                  <Trash2 className="size-3.5" />
                </Button>
              }
              title="Remover dado"
              description={`Remover "${item.key}" dos dados coletados?`}
              confirmLabel="Remover"
              destructive
              onConfirm={() => onDelete(item.id)}
            />
          </>
        )}
      </div>
    </div>
  );
}

function AddExtractedDataForm({ category, onAdd }: { category: string; onAdd: (key: string, value: string) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState("");
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!key.trim() || !value.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onAdd(key.trim(), value.trim());
      setKey("");
      setValue("");
      setOpen(false);
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <Button size="sm" variant="outline" className="w-fit" onClick={() => setOpen(true)}>
        <Plus className="size-3.5" /> Adicionar em {CATEGORY_LABEL[category] ?? category}
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-dashed p-3">
      <Input placeholder="Chave (ex: horario_funcionamento)" value={key} onChange={(event) => setKey(event.target.value)} />
      <Input placeholder="Valor" value={value} onChange={(event) => setValue(event.target.value)} />
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      <div className="flex gap-2">
        <Button size="sm" onClick={submit} disabled={saving || !key.trim() || !value.trim()}>
          Salvar
        </Button>
        <Button size="sm" variant="outline" onClick={() => setOpen(false)} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

function FaqRow({ faq, onDelete }: { faq: FaqItem; onDelete: (id: string) => Promise<void> }) {
  return (
    <div className="flex items-start justify-between gap-2 rounded-md border px-3 py-2 text-sm">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="font-medium">P: {faq.question}</span>
        <span className="text-muted-foreground">R: {faq.answer}</span>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="outline" className="text-xs">
            {faq.category}
          </Badge>
          <span>Perguntado {faq.frequency}x</span>
        </div>
      </div>
      <ConfirmDialog
        trigger={
          <Button size="icon" variant="ghost" className="size-7 shrink-0">
            <Trash2 className="size-3.5" />
          </Button>
        }
        title="Remover FAQ"
        description="Remover esta pergunta frequente dos dados coletados?"
        confirmLabel="Remover"
        destructive
        onConfirm={() => onDelete(faq.id)}
      />
    </div>
  );
}

function AddFaqForm({ onAdd }: { onAdd: (question: string, answer: string) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!question.trim() || !answer.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onAdd(question.trim(), answer.trim());
      setQuestion("");
      setAnswer("");
      setOpen(false);
    } catch (err) {
      setError(errorMessage(err, GENERIC_SAVE_ERROR_MESSAGE));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <Button size="sm" variant="outline" className="w-fit" onClick={() => setOpen(true)}>
        <Plus className="size-3.5" /> Adicionar FAQ
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border border-dashed p-3">
      <Input placeholder="Pergunta" value={question} onChange={(event) => setQuestion(event.target.value)} />
      <Textarea placeholder="Resposta" value={answer} onChange={(event) => setAnswer(event.target.value)} className="min-h-20" />
      {error ? <FormStatus tone="error">{error}</FormStatus> : null}
      <div className="flex gap-2">
        <Button size="sm" onClick={submit} disabled={saving || !question.trim() || !answer.trim()}>
          Salvar
        </Button>
        <Button size="sm" variant="outline" onClick={() => setOpen(false)} disabled={saving}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

function PatternRow({ pattern }: { pattern: AttendantPattern }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-xs">
          {pattern.pattern_type}
        </Badge>
        <span className="text-xs text-muted-foreground">detectado {pattern.frequency}x</span>
      </div>
      <span>{pattern.description}</span>
      {pattern.examples.length > 0 ? (
        <span className="text-xs text-muted-foreground">Exemplos: {pattern.examples.slice(0, 3).join(" | ")}</span>
      ) : null}
    </div>
  );
}

function InstanceData({ instanceId }: { instanceId: string }) {
  const {
    data: readiness,
    error: readinessError,
    loading: readinessLoading,
    reload: reloadReadiness,
  } = useAsyncData(() => apiFetch<DataReadiness>(`/instances/${instanceId}/analytics/readiness`), [instanceId]);
  const {
    data: extracted,
    error: extractedError,
    loading: extractedLoading,
    reload: reloadExtracted,
  } = useAsyncData(() => apiFetch<ExtractedData[]>(`/instances/${instanceId}/analytics/extracted-data`), [instanceId]);
  const {
    data: faqs,
    error: faqsError,
    loading: faqsLoading,
    reload: reloadFaqs,
  } = useAsyncData(() => apiFetch<FaqItem[]>(`/instances/${instanceId}/analytics/faqs`), [instanceId]);
  const {
    data: patterns,
    error: patternsError,
    loading: patternsLoading,
    reload: reloadPatterns,
  } = useAsyncData(() => apiFetch<AttendantPattern[]>(`/instances/${instanceId}/analytics/patterns`), [instanceId]);

  const [generating, setGenerating] = useState(false);
  const [generateStatus, setGenerateStatus] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const byCategory = useMemo(() => {
    const grouped: Record<string, ExtractedData[]> = { business_info: [], products_services: [], policies: [] };
    for (const item of extracted ?? []) {
      (grouped[item.category] ??= []).push(item);
    }
    return grouped;
  }, [extracted]);

  async function handleGeneratePrompt() {
    setGenerating(true);
    setGenerateStatus(null);
    try {
      const generated = await apiFetch<GeneratedPrompt>(`/instances/${instanceId}/analytics/generate-prompt`, {
        method: "POST",
      });
      setGenerateStatus({
        tone: "success",
        text: `Prompt v${generated.version_number} gerado e aguardando aprovacao na pagina Prompt.`,
      });
      toast.success("Novo prompt gerado. Revise e aprove na pagina Prompt.");
    } catch (err) {
      setGenerateStatus({ tone: "error", text: errorMessage(err, "Nao foi possivel gerar o prompt.") });
    } finally {
      setGenerating(false);
    }
  }

  const loading = readinessLoading || extractedLoading || faqsLoading || patternsLoading;
  const loadError = readinessError ?? extractedError ?? faqsError ?? patternsError;

  if (loading) return <LoadingState />;
  if (loadError) {
    return (
      <ErrorState
        message={loadError}
        onRetry={() => {
          reloadReadiness();
          reloadExtracted();
          reloadFaqs();
          reloadPatterns();
        }}
      />
    );
  }
  if (!readiness) return null;

  const totalPatterns = (patterns ?? []).filter((p) => p.pattern_type !== "personality_trait");
  const traits = (patterns ?? []).filter((p) => p.pattern_type === "personality_trait");

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-3 pt-6">
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span>
              <strong>{readiness.analyzed_conversations}</strong> conversas analisadas
            </span>
            <span>
              <strong>{readiness.total_extracted}</strong> dados extraidos
            </span>
            <span>
              <strong>{readiness.total_faqs}</strong> FAQs
            </span>
            <span>
              <strong>{readiness.total_patterns}</strong> padroes
            </span>
          </div>
          {readiness.ready ? (
            <Button size="sm" className="w-fit" onClick={handleGeneratePrompt} disabled={generating}>
              <Sparkles className="size-3.5" />
              {generating ? "Gerando..." : "Gerar prompt com IA a partir dos dados"}
            </Button>
          ) : (
            <p className="text-sm text-muted-foreground">
              Ainda nao ha conversas analisadas. O agente aprende automaticamente conforme atende clientes pelo
              WhatsApp; volte aqui depois de algumas conversas.
            </p>
          )}
          {generateStatus ? <FormStatus tone={generateStatus.tone}>{generateStatus.text}</FormStatus> : null}
        </CardContent>
      </Card>

      {(["business_info", "products_services", "policies"] as const).map((category) => (
        <Section key={category} title={CATEGORY_LABEL[category]} icon={CATEGORY_ICON[category]} count={byCategory[category].length}>
          {byCategory[category].length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum dado coletado ainda nesta categoria.</p>
          ) : null}
          {byCategory[category].map((item) => (
            <ExtractedRow
              key={item.id}
              item={item}
              onSave={async (id, value) => {
                await apiFetch(`/instances/${instanceId}/analytics/extracted-data/${id}`, {
                  method: "PUT",
                  body: JSON.stringify({ value }),
                });
                reloadExtracted();
              }}
              onDelete={async (id) => {
                await apiFetch(`/instances/${instanceId}/analytics/extracted-data/${id}`, { method: "DELETE" });
                reloadExtracted();
              }}
            />
          ))}
          <AddExtractedDataForm
            category={category}
            onAdd={async (key, value) => {
              await apiFetch(`/instances/${instanceId}/analytics/extracted-data`, {
                method: "POST",
                body: JSON.stringify({ category, key, value }),
              });
              reloadExtracted();
            }}
          />
        </Section>
      ))}

      <Section title="Perguntas frequentes" icon={HelpCircle} count={(faqs ?? []).length}>
        {(faqs ?? []).length === 0 ? <p className="text-sm text-muted-foreground">Nenhuma FAQ coletada ainda.</p> : null}
        {(faqs ?? []).map((faq) => (
          <FaqRow
            key={faq.id}
            faq={faq}
            onDelete={async (id) => {
              await apiFetch(`/instances/${instanceId}/analytics/faqs/${id}`, { method: "DELETE" });
              reloadFaqs();
            }}
          />
        ))}
        <AddFaqForm
          onAdd={async (question, answer) => {
            await apiFetch(`/instances/${instanceId}/analytics/faqs`, {
              method: "POST",
              body: JSON.stringify({ question, answer }),
            });
            reloadFaqs();
          }}
        />
      </Section>

      <Section title="Padroes de atendimento" icon={Users} count={totalPatterns.length} defaultOpen={false}>
        {totalPatterns.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum padrao detectado ainda.</p>
        ) : (
          totalPatterns.map((pattern) => <PatternRow key={pattern.id} pattern={pattern} />)
        )}
        {traits.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 pt-2">
            {traits.map((trait) => (
              <Badge key={trait.id} variant="secondary">
                {trait.description}
              </Badge>
            ))}
          </div>
        ) : null}
      </Section>
    </div>
  );
}

export function DadosColetadosView({ instanceId }: { instanceId: string }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold">Dados coletados</h1>
        <p className="text-sm text-muted-foreground">
          Informacoes extraidas automaticamente das conversas do WhatsApp para manter o prompt do agente
          atualizado.
        </p>
      </div>
      <InstanceData instanceId={instanceId} />
    </div>
  );
}

export default function DadosColetadosPage() {
  const { instances, selectedId, error, reload } = useOwnInstances();

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (instances === null) return <LoadingState />;

  if (instances.length === 0 || !selectedId) {
    return (
      <div className="flex flex-col gap-2">
        <h1 className="text-xl font-semibold">Dados coletados</h1>
        <EmptyState title="Nenhuma instancia associada a sua conta ainda." />
      </div>
    );
  }

  return <DadosColetadosView instanceId={selectedId} />;
}
