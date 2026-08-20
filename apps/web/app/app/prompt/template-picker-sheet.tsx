"use client";

import { useState } from "react";
import { LayoutTemplate } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import type { PromptTemplate } from "@/lib/types";

/** Compact template picker embedded in the prompt editor header. Replaces the old standalone
 * `/app/prompt/templates` gallery page (heavy 3-col card grid + sessionStorage handoff to the
 * editor). Selecting a template hands its content straight to the caller via `onSelect` -
 * everything happens in the same mounted editor, no navigation involved. */
export function TemplatePickerSheet({ onSelect }: { onSelect: (template: PromptTemplate) => void }) {
  const [open, setOpen] = useState(false);
  const {
    data: templates,
    error,
    loading,
    reload,
  } = useAsyncData(() => (open ? apiFetch<PromptTemplate[]>("/prompt-templates") : Promise.resolve(null)), [open]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm">
          <LayoutTemplate className="size-4" />
          Usar template
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Templates de prompt</SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-1 px-4 pb-4">
          {loading ? <LoadingState /> : null}
          {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
          {!loading && !error && templates?.length === 0 ? (
            <EmptyState title="Nenhum template disponivel ainda." icon={LayoutTemplate} />
          ) : null}
          {!loading && !error
            ? templates?.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => {
                    onSelect(template);
                    setOpen(false);
                  }}
                  className="flex flex-col gap-1 rounded-md border border-transparent px-3 py-2.5 text-left transition-colors hover:border-border hover:bg-muted/50"
                >
                  <div className="flex items-center gap-2">
                    <span className="leading-none">{template.icon_emoji}</span>
                    <span className="text-sm font-medium">{template.title}</span>
                    <Badge variant="outline" className="ml-auto text-[10px] font-normal">
                      {template.niche}
                    </Badge>
                  </div>
                  <p className="line-clamp-2 text-xs text-muted-foreground">{template.description}</p>
                </button>
              ))
            : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
