"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api-client";
import { PENDING_TEMPLATE_KEY } from "@/lib/constants";
import type { PromptTemplate } from "@/lib/types";

export default function PromptTemplateGalleryPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);

  useEffect(() => {
    apiFetch<PromptTemplate[]>("/prompt-templates").then(setTemplates);
  }, []);

  function useTemplate(template: PromptTemplate) {
    sessionStorage.setItem(
      PENDING_TEMPLATE_KEY,
      JSON.stringify({ content: template.content, title: template.title })
    );
    router.push("/app/prompt");
  }

  const byNiche = templates.reduce<Record<string, PromptTemplate[]>>((acc, template) => {
    (acc[template.niche] ??= []).push(template);
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Templates de prompt</h1>
      {Object.entries(byNiche).map(([niche, items]) => (
        <div key={niche} className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-muted-foreground">{niche}</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((template) => (
              <Card key={template.id}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <span>{template.icon_emoji}</span>
                    {template.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  <p className="text-sm text-muted-foreground">{template.description}</p>
                  <Button size="sm" onClick={() => useTemplate(template)} className="w-fit">
                    Usar este template
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
      {templates.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum template disponivel ainda.</p>
      ) : null}
    </div>
  );
}
