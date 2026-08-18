"use client";

import { useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import type { DataReadiness } from "@/lib/types";

const THINKING_PHRASES = [
  "Pensando...",
  "Adotando novas medidas...",
  "Conhecimento nunca e demais!",
  "Fome de saber",
  "Conectando padroes...",
  "Absorvendo cada conversa...",
] as const;

/** Computes a 0-100 "knowledge score" from the same counters the readiness card above it
 * already shows, weighted so richer signal types (FAQs, patterns) count for more than raw
 * conversation volume. Purely a UI summary - actual prompt quality is still judged by a human
 * approving the generated version, this never gates anything. */
function knowledgeScore(readiness: DataReadiness): number {
  const raw =
    readiness.analyzed_conversations * 2 +
    readiness.total_extracted * 3 +
    readiness.total_faqs * 4 +
    readiness.total_patterns * 3;
  return Math.max(0, Math.min(100, raw));
}

function scoreLabel(score: number): string {
  if (score === 0) return "Ainda sem conhecimento";
  if (score < 30) return "Aprendendo o basico";
  if (score < 60) return "Conhecimento em formacao";
  if (score < 85) return "Boa base de conhecimento";
  return "Conhecimento avancado";
}

/** Illustrative "brain" widget for the dados-coletados tab: visualizes how much signal the AI
 * has absorbed so far and rotates through short status phrases, reinforcing that learning
 * happens automatically as conversations come in. Decorative, but the score is derived from
 * real readiness counters rather than being purely cosmetic. */
export function AiBrainPreview({ readiness }: { readiness: DataReadiness }) {
  const score = knowledgeScore(readiness);
  const [phraseIndex, setPhraseIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setPhraseIndex((i) => (i + 1) % THINKING_PHRASES.length);
    }, 2800);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex items-center gap-4 rounded-lg border bg-muted/20 p-4">
      <div className="relative flex size-16 shrink-0 items-center justify-center">
        <span className="absolute inset-0 animate-ping rounded-full bg-primary/20 [animation-duration:2.5s]" />
        <span className="absolute inset-1 rounded-full bg-primary/10" />
        <Brain
          className="relative size-9 text-primary transition-opacity duration-700"
          style={{ opacity: 0.4 + (score / 100) * 0.6 }}
        />
      </div>
      <div className="flex flex-1 flex-col gap-1.5">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium">{scoreLabel(score)}</p>
          <span className="text-xs text-muted-foreground">{score}/100</span>
        </div>
        <Progress value={score} />
        <p key={phraseIndex} className="animate-in fade-in text-xs text-muted-foreground italic duration-500">
          {THINKING_PHRASES[phraseIndex]}
        </p>
      </div>
    </div>
  );
}
