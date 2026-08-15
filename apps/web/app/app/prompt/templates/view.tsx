"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/state";
import { apiFetch } from "@/lib/api-client";
import { useAsyncData } from "@/lib/use-async-data";
import { PENDING_TEMPLATE_KEY } from "@/lib/constants";
import type { PromptTemplate } from "@/lib/types";

export default function PromptTemplateGalleryView() {
  const router = useRouter();
  const {
    data: templates,
    error,
    loading,
    reload,
  } = useAsyncData(() => apiFetch<PromptTemplate[]>("/prompt-templates"), []);

  function selectTemplate(template: PromptTemplate) {
    sessionStorage.setItem(
      PENDING_TEMPLATE_KEY,
      JSON.stringify({ content: template.content, title: template.title })
    );
    router.push("/app/prompt");
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Templates de prompt</h1>
      {loading ? <LoadingState /> : null}
      {!loading && error ? <ErrorState message={error} onRetry={reload} /> : null}
      {!loading && !error && templates && templates.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <Card key={template.id}>
              <CardHeader>
                <Badge variant="secondary" className="w-fit">
                  {template.niche}
                </Badge>
                <CardTitle className="flex items-center gap-2 text-base">
                  <span>{template.icon_emoji}</span>
                  {template.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <p className="text-sm text-muted-foreground">{template.description}</p>
                <Button size="sm" onClick={() => selectTemplate(template)} className="w-fit">
                  Usar este template
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
      {!loading && !error && templates?.length === 0 ? (
        <EmptyState title="Nenhum template disponivel ainda." />
      ) : null}
    </div>
  );
}
