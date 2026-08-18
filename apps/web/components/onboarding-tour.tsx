"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

export interface OnboardingStep {
  /** CSS selector for the element to spotlight (e.g. `[data-tour="/admin"]`). */
  target: string;
  title: string;
  description: string;
}

function TourCard({
  stepIndex,
  totalSteps,
  step,
  onPrev,
  onNext,
  onSkip,
  onFinish,
}: {
  stepIndex: number;
  totalSteps: number;
  step: OnboardingStep;
  onPrev: () => void;
  onNext: () => void;
  onSkip: () => void;
  onFinish: () => void;
}) {
  const isLast = stepIndex === totalSteps - 1;
  return (
    <>
      <p className="text-xs text-muted-foreground">
        {stepIndex + 1} de {totalSteps}
      </p>
      <p className="mt-1 text-sm font-semibold">{step.title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
      <div className="mt-3 flex items-center justify-between gap-2">
        <Button variant="ghost" size="sm" onClick={onSkip}>
          Pular tour
        </Button>
        <div className="flex gap-2">
          {stepIndex > 0 ? (
            <Button variant="outline" size="sm" onClick={onPrev}>
              Voltar
            </Button>
          ) : null}
          <Button size="sm" onClick={isLast ? onFinish : onNext}>
            {isLast ? "Concluir" : "Proximo"}
          </Button>
        </div>
      </div>
    </>
  );
}

/** Spotlight overlay that walks the user through a fixed sequence of page elements, one at a
 * time. Purely presentational/controlled - callers own the current step index and persistence
 * (e.g. "already seen this tour") via `onSkip`/`onFinish`. Recomputes the target's position on
 * every step change, window resize and scroll so the highlight always tracks the real element;
 * falls back to a centered card when the target isn't currently in the DOM (e.g. a sidebar
 * collapsed on a small viewport), so the tour never strands the user on a blank overlay. */
export function OnboardingTour({
  steps,
  stepIndex,
  onNext,
  onPrev,
  onSkip,
  onFinish,
}: {
  steps: OnboardingStep[];
  stepIndex: number;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  onFinish: () => void;
}) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const step = steps[stepIndex];

  useEffect(() => {
    if (!step) return;
    function measure() {
      const el = step ? document.querySelector(step.target) : null;
      setRect(el ? el.getBoundingClientRect() : null);
    }
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [step]);

  if (!step) return null;

  const cardProps = {
    stepIndex,
    totalSteps: steps.length,
    step,
    onPrev,
    onNext,
    onSkip,
    onFinish,
  };

  if (!rect) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
        <div className="w-full max-w-sm rounded-lg border bg-popover p-4 text-popover-foreground shadow-lg">
          <TourCard {...cardProps} />
        </div>
      </div>
    );
  }

  const padding = 8;
  const highlightStyle = {
    top: rect.top - padding,
    left: rect.left - padding,
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  };
  const cardWidth = 288;
  const tooltipTop = Math.min(rect.bottom + padding + 8, window.innerHeight - 200);
  const tooltipLeft = Math.min(Math.max(rect.left, 16), window.innerWidth - cardWidth - 16);

  return (
    <div className="fixed inset-0 z-50">
      <div
        className="pointer-events-none absolute rounded-lg ring-2 ring-primary transition-all duration-300"
        style={{ ...highlightStyle, boxShadow: "0 0 0 9999px rgba(0,0,0,0.55)" }}
      />
      <div
        className="absolute rounded-lg border bg-popover p-4 text-popover-foreground shadow-lg"
        style={{ top: tooltipTop, left: tooltipLeft, width: cardWidth }}
      >
        <TourCard {...cardProps} />
      </div>
    </div>
  );
}
