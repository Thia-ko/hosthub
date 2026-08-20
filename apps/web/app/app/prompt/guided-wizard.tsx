"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

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

const FULL_TEXT_KEY = "prompt-completo" as const;
type NavKey = SectionKey | typeof FULL_TEXT_KEY;

const NAV_KEYS: NavKey[] = [...SECTIONS.map((s) => s.key), FULL_TEXT_KEY];

const FORMALITY_OPTIONS = ["Muito informal", "Informal", "Neutro", "Formal", "Muito formal"] as const;

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

/** Appends `sentence` to a section's existing text on its own line - used by the quick-fill
 * helpers below so clicking "Adicionar ao texto" never clobbers what's already there. */
function appendLine(existing: string, sentence: string): string {
  const trimmed = existing.trim();
  return trimmed ? `${trimmed}\n${sentence}` : sentence;
}

/** Unified, non-technical hub for building the agent's prompt: all sections the auto-generation
 * pipeline fills from real conversations are stacked vertically (no tab/step navigation to get
 * lost in), with a sticky side nav for quick jumps and a scroll-based highlight of the current
 * section. A couple of sections (tone, business info) also offer small structured pickers that
 * compose a suggested sentence into the free-text box on click, for people who don't know what
 * to write from a blank page - every section still boils down to plain text underneath, so
 * nothing here is mandatory. The last "Prompt completo" section is the exact text that gets
 * saved: normally kept in sync with the sections above, but directly editable too (replaces the
 * old separate "Avancado" mode - there's only one view now). Seeds itself once from
 * `initialContent` - callers remount it (via `key`) when the underlying prompt version changes. */
export function GuidedWizard({
  initialContent,
  onAssembledChange,
}: {
  initialContent: string;
  onAssembledChange: (content: string) => void;
}) {
  const [answers, setAnswers] = useState<Record<SectionKey, string>>(() => parseInitialAnswers(initialContent));
  const [fullText, setFullText] = useState(initialContent);
  const [activeKey, setActiveKey] = useState<NavKey>(SECTIONS[0].key);

  const [formality, setFormality] = useState("");
  const [usesEmojis, setUsesEmojis] = useState(false);
  const [usesSlang, setUsesSlang] = useState(false);

  const [businessName, setBusinessName] = useState("");
  const [businessAddress, setBusinessAddress] = useState("");
  const [businessHours, setBusinessHours] = useState("");
  const [businessContact, setBusinessContact] = useState("");

  const sectionRefs = useRef<Record<NavKey, HTMLDivElement | null>>({} as Record<NavKey, HTMLDivElement | null>);

  useEffect(() => {
    function updateActiveFromScroll() {
      const threshold = 120;
      let current: NavKey = NAV_KEYS[0];
      for (const key of NAV_KEYS) {
        const el = sectionRefs.current[key];
        if (!el) continue;
        if (el.getBoundingClientRect().top <= threshold) {
          current = key;
        } else {
          break;
        }
      }
      setActiveKey(current);
    }

    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        updateActiveFromScroll();
        ticking = false;
      });
    }

    updateActiveFromScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  function updateAnswer(key: SectionKey, value: string) {
    const next = { ...answers, [key]: value };
    setAnswers(next);
    const assembled = assemble(next);
    setFullText(assembled);
    onAssembledChange(assembled);
  }

  function updateFullText(value: string) {
    setFullText(value);
    onAssembledChange(value);
  }

  function scrollToSection(key: NavKey) {
    sectionRefs.current[key]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function insertToneSuggestion() {
    const parts = [
      formality ? `Tom ${formality.toLowerCase()}` : null,
      usesEmojis ? "usa emojis com moderacao" : "nao usa emojis",
      usesSlang ? "usa girias e expressoes informais" : "evita girias",
    ].filter((part): part is string => part !== null);
    if (parts.length === 0) return;
    updateAnswer("tom", appendLine(answers.tom, `${parts.join(", ")}.`));
  }

  function insertBusinessInfo() {
    const parts = [
      businessName,
      businessAddress,
      businessHours ? `Horario: ${businessHours}` : "",
      businessContact ? `Contato: ${businessContact}` : "",
    ].filter((part) => part.trim());
    if (parts.length === 0) return;
    updateAnswer("negocio", appendLine(answers.negocio, `${parts.join(". ")}.`));
  }

  function navButtonClass(key: NavKey): string {
    return cn(
      "relative flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors duration-150",
      activeKey === key
        ? "bg-accent/60 font-medium text-foreground"
        : "font-normal text-muted-foreground/70 hover:bg-accent/30 hover:text-foreground"
    );
  }

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      <nav className="flex gap-1 overflow-x-auto pb-1 lg:sticky lg:top-4 lg:order-2 lg:w-52 lg:shrink-0 lg:flex-col lg:overflow-visible lg:border-l lg:border-border/40 lg:pb-0 lg:pl-4">
        {SECTIONS.map((section) => (
          <button
            key={section.key}
            type="button"
            onClick={() => scrollToSection(section.key)}
            className={navButtonClass(section.key)}
          >
            <span
              aria-hidden
              className={cn(
                "absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary transition-opacity",
                activeKey === section.key ? "opacity-100" : "opacity-0"
              )}
            />
            {section.title}
            {answers[section.key]?.trim() ? (
              <span aria-hidden className="ml-auto size-1.5 shrink-0 rounded-full bg-primary" />
            ) : null}
          </button>
        ))}
        <button type="button" onClick={() => scrollToSection(FULL_TEXT_KEY)} className={navButtonClass(FULL_TEXT_KEY)}>
          <span
            aria-hidden
            className={cn(
              "absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary transition-opacity",
              activeKey === FULL_TEXT_KEY ? "opacity-100" : "opacity-0"
            )}
          />
          Prompt completo
        </button>
      </nav>

      <div className="flex flex-1 flex-col gap-4">
        {SECTIONS.map((section) => (
          <div
            key={section.key}
            id={`wizard-section-${section.key}`}
            ref={(el) => {
              sectionRefs.current[section.key] = el;
            }}
            className="scroll-mt-20 rounded-lg border p-4"
          >
            <label className="text-sm font-semibold" htmlFor={`wizard-textarea-${section.key}`}>
              {section.title}
            </label>
            <p className="text-sm text-muted-foreground">{section.description}</p>

            {section.key === "tom" ? (
              <div className="mt-3 flex flex-wrap items-end gap-3 rounded-md bg-muted/30 p-3">
                <div className="flex flex-col gap-1.5">
                  <Label className="text-xs">Formalidade</Label>
                  <Select value={formality} onValueChange={setFormality}>
                    <SelectTrigger className="w-40">
                      <SelectValue placeholder="Escolher" />
                    </SelectTrigger>
                    <SelectContent>
                      {FORMALITY_OPTIONS.map((option) => (
                        <SelectItem key={option} value={option}>
                          {option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <label className="flex items-center gap-1.5 text-sm">
                  <Checkbox checked={usesEmojis} onCheckedChange={(checked) => setUsesEmojis(checked === true)} />
                  Usa emojis
                </label>
                <label className="flex items-center gap-1.5 text-sm">
                  <Checkbox checked={usesSlang} onCheckedChange={(checked) => setUsesSlang(checked === true)} />
                  Usa girias
                </label>
                <Button type="button" size="sm" variant="outline" onClick={insertToneSuggestion}>
                  Adicionar ao texto
                </Button>
              </div>
            ) : null}

            {section.key === "negocio" ? (
              <div className="mt-3 flex flex-col gap-2 rounded-md bg-muted/30 p-3">
                <div className="grid gap-2 sm:grid-cols-2">
                  <Input
                    placeholder="Nome do negocio"
                    value={businessName}
                    onChange={(event) => setBusinessName(event.target.value)}
                  />
                  <Input
                    placeholder="Endereco"
                    value={businessAddress}
                    onChange={(event) => setBusinessAddress(event.target.value)}
                  />
                  <Input
                    placeholder="Horario de funcionamento"
                    value={businessHours}
                    onChange={(event) => setBusinessHours(event.target.value)}
                  />
                  <Input
                    placeholder="Telefone/contato"
                    value={businessContact}
                    onChange={(event) => setBusinessContact(event.target.value)}
                  />
                </div>
                <Button type="button" size="sm" variant="outline" className="w-fit" onClick={insertBusinessInfo}>
                  Adicionar ao texto
                </Button>
              </div>
            ) : null}

            <Textarea
              id={`wizard-textarea-${section.key}`}
              className="mt-3 min-h-32"
              value={answers[section.key]}
              placeholder={section.placeholder}
              onChange={(event) => updateAnswer(section.key, event.target.value)}
            />
          </div>
        ))}

        <div
          id={`wizard-section-${FULL_TEXT_KEY}`}
          ref={(el) => {
            sectionRefs.current[FULL_TEXT_KEY] = el;
          }}
          className="scroll-mt-20 rounded-lg border p-4"
        >
          <label className="text-sm font-semibold" htmlFor="wizard-full-text">
            Prompt completo
          </label>
          <p className="text-sm text-muted-foreground">
            Texto final que sera salvo. Montado automaticamente a partir das etapas acima, mas pode ser editado
            direto aqui se preferir.
          </p>
          <Textarea
            id="wizard-full-text"
            className="mt-3 min-h-96 font-mono text-sm"
            value={fullText}
            onChange={(event) => updateFullText(event.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
