"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";

/** Sections mirror the exact headings `prompt_generator.py` asks the AI to produce
 * (`_build_full_generation_prompt`), so a prompt built here diffs cleanly against one the
 * auto-generation pipeline created from real conversations, and either can be edited by the
 * other later. */
const SECTIONS = [
  {
    key: "identidade",
    heading: "Identidade",
    title: "Identidade do agente",
    description: "Quem e o agente e qual e a missao do estabelecimento.",
    placeholder:
      "Ex: Voce e a Sofia, atendente virtual da Doce Sabor Confeitaria. Sua missao e ajudar clientes a escolher e encomendar bolos e doces com simpatia e agilidade.",
  },
  {
    key: "tom",
    heading: "Tom e Personalidade",
    title: "Tom e personalidade",
    description: "Como o agente se comunica: formalidade, uso de emojis, girias.",
    placeholder:
      "Ex: Tom informal e caloroso, usa emojis com moderacao, trata o cliente por 'voce', evita respostas robotizadas.",
  },
  {
    key: "negocio",
    heading: "Informacoes do Negocio",
    title: "Informacoes do negocio",
    description: "Nome, endereco, horario de funcionamento, contato.",
    placeholder: "Ex: Doce Sabor Confeitaria, Rua das Flores 123, aberto seg-sab das 9h as 19h, (11) 99999-0000.",
  },
  {
    key: "produtos",
    heading: "Produtos e Servicos",
    title: "Produtos e servicos",
    description: "Lista do que voce vende, com precos se tiver.",
    placeholder: "Ex: Bolo de chocolate (R$ 80), Torta de morango (R$ 95), Docinhos (R$ 3,50 a unidade).",
  },
  {
    key: "politicas",
    heading: "Politicas",
    title: "Politicas",
    description: "Regras de pagamento, entrega, troca e cancelamento.",
    placeholder: "Ex: Pagamento via Pix ou cartao. Entrega em ate 2 dias uteis. Cancelamento gratuito ate 24h antes.",
  },
  {
    key: "faqs",
    heading: "Perguntas Frequentes",
    title: "Perguntas frequentes",
    description: "Pares de pergunta e resposta que os clientes mais fazem.",
    placeholder: "P: Voces entregam aos domingos?\nR: Nao, funcionamos de segunda a sabado.",
  },
  {
    key: "regras",
    heading: "Regras de Atendimento",
    title: "Regras de atendimento",
    description: "Comportamentos obrigatorios e proibidos do agente.",
    placeholder:
      "Ex: Nunca prometa prazos que nao pode cumprir. Sempre confirme o pedido antes de fechar. Nunca fale sobre concorrentes.",
  },
  {
    key: "situacoes",
    heading: "Como Lidar com Situacoes Dificeis",
    title: "Situacoes dificeis",
    description: "Reclamacoes, preco alto, indisponibilidade, quando chamar um humano.",
    placeholder:
      "Ex: Se o cliente reclamar, peca desculpas e ofereca uma solucao. Se pedirem para falar com humano, avise que vai chamar o atendente.",
  },
] as const;

type SectionKey = (typeof SECTIONS)[number]["key"];

function parseInitialAnswers(content: string): Record<SectionKey, string> {
  const matches = [...content.matchAll(/^##\s+(.+)$/gm)];
  const bodyFor = (heading: string): string => {
    const index = matches.findIndex((match) => match[1].trim() === heading);
    if (index === -1) return "";
    const start = (matches[index].index ?? 0) + matches[index][0].length;
    const end = index + 1 < matches.length ? matches[index + 1].index : content.length;
    return content.slice(start, end).trim();
  };
  return Object.fromEntries(SECTIONS.map((s) => [s.key, bodyFor(s.heading)])) as Record<SectionKey, string>;
}

function assemble(answers: Record<SectionKey, string>): string {
  return SECTIONS.map((s) => answers[s.key]?.trim())
    .map((body, index) => (body ? `## ${SECTIONS[index].heading}\n${body}` : null))
    .filter((block): block is string => block !== null)
    .join("\n\n");
}

/** Guided, non-technical alternative to the raw prompt textarea: walks the same sections the
 * auto-generation pipeline fills from real conversations, one at a time, then assembles them
 * into the identical section format. Seeds itself once from `initialContent` - callers remount
 * it (via `key`) when the underlying prompt version changes. */
export function GuidedWizard({
  initialContent,
  onAssembledChange,
}: {
  initialContent: string;
  onAssembledChange: (content: string) => void;
}) {
  const [answers, setAnswers] = useState<Record<SectionKey, string>>(() => parseInitialAnswers(initialContent));
  const [step, setStep] = useState(0);
  const assembled = useMemo(() => assemble(answers), [answers]);
  const isReview = step === SECTIONS.length;
  const totalSteps = SECTIONS.length + 1;

  function updateAnswer(key: SectionKey, value: string) {
    const next = { ...answers, [key]: value };
    setAnswers(next);
    onAssembledChange(assemble(next));
  }

  const current = SECTIONS[step];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Progress value={((step + 1) / totalSteps) * 100} />
        <p className="text-xs text-muted-foreground">
          Etapa {step + 1} de {totalSteps} - {isReview ? "Revisao" : current.title}
        </p>
      </div>

      {!isReview ? (
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium" htmlFor={`wizard-${current.key}`}>
            {current.title}
          </label>
          <p className="text-sm text-muted-foreground">{current.description}</p>
          <Textarea
            id={`wizard-${current.key}`}
            className="min-h-40"
            value={answers[current.key]}
            placeholder={current.placeholder}
            onChange={(event) => updateAnswer(current.key, event.target.value)}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          <p className="text-sm font-medium">Prompt montado</p>
          <p className="text-sm text-muted-foreground">
            Confira o resultado. Use &quot;Salvar nova versao&quot; abaixo para publicar, ou volte para ajustar alguma etapa.
          </p>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border bg-muted/30 p-3 font-mono text-xs">
            {assembled || "(nenhuma etapa preenchida ainda)"}
          </pre>
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
          Voltar
        </Button>
        <Button onClick={() => setStep((s) => Math.min(SECTIONS.length, s + 1))} disabled={isReview}>
          Avancar
        </Button>
      </div>
    </div>
  );
}
