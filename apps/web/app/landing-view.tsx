import Link from "next/link";
import { Bot, Cable, Megaphone, Workflow, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandLockup } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";
import { DemoChatWidget } from "@/components/demo-chat-widget";

/** The 4 pillars mirror `app/services/plans.py::PLAN_DEFAULTS` exactly - this is the real
 * feature matrix the backend gates on, not aspirational copy. Card sizing (bento, not a
 * uniform grid) reflects that hierarchy: IA + atendimento humanizado is the core every plan
 * ships with, so it gets the dominant tile; the other three are the differentiators between
 * tiers. */
const PILLARS: {
  icon: LucideIcon;
  title: string;
  description: string;
  tier: string;
  span: string;
}[] = [
  {
    icon: Bot,
    title: "IA + Atendimento Humanizado",
    description:
      "O agente responde no WhatsApp 24/7 com base no que você configurar, mas sabe reconhecer quando o assunto exige um humano — reclamação, reembolso ou pedido explícito — e passa o bastão sem deixar o cliente esperando. Depois de cada conversa, uma pesquisa de satisfação mede a nota de verdade.",
    tier: "Incluso em todo plano",
    span: "sm:col-span-2 lg:col-span-2 lg:row-span-2",
  },
  {
    icon: Workflow,
    title: "Chatbot sem IA",
    description:
      "Árvore de menu por número ou palavra-chave, sem custo de token — alternativa determinística pra quem quer um fluxo simples de atendimento, ou complemento pro que a IA já faz.",
    tier: "Disponível em qualquer plano",
    span: "lg:col-span-2",
  },
  {
    icon: Megaphone,
    title: "Campanhas em massa",
    description: "Disparos respeitando a janela de 24h do WhatsApp automaticamente, sem risco de bloqueio.",
    tier: "A partir do Pro",
    span: "",
  },
  {
    icon: Cable,
    title: "API para desenvolvedores",
    description: "Chaves de API e webhooks de saída pra integrar com n8n ou o sistema da sua própria equipe.",
    tier: "A partir do Enterprise",
    span: "",
  },
];

const HOW_IT_WORKS_STEPS = [
  {
    title: "Configure o agente",
    description:
      "Responda o wizard guiado (identidade, produtos, políticas, FAQ) ou envie arquivos de conhecimento — texto, imagem ou áudio.",
  },
  {
    title: "Conecte o WhatsApp",
    description: "Escaneie um QR code ou informe as credenciais da API oficial da Meta.",
  },
  {
    title: "A IA atende e aprende",
    description: "Cada conversa é analisada para sugerir melhorias no prompt e manter as respostas atualizadas.",
  },
  {
    title: "Acompanhe o impacto",
    description: "Dashboard com mensagens, tokens, taxa de resolução pela IA e satisfação dos clientes.",
  },
];

export default function LandingView() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b px-4 py-3 sm:px-8">
        <BrandLockup />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button variant="outline" asChild>
            <Link href="/login">Entrar</Link>
          </Button>
        </div>
      </header>

      <main className="flex-1">
        <section className="relative overflow-hidden">
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
            <div className="absolute -top-24 -left-32 size-96 rounded-full bg-primary/15 blur-3xl motion-safe:animate-[mesh-drift_16s_ease-in-out_infinite]" />
            <div className="absolute top-1/3 -right-24 size-80 rounded-full bg-chart-2/10 blur-3xl" />
            <div className="absolute -bottom-32 left-1/4 size-72 rounded-full bg-primary/10 blur-3xl" />
          </div>

          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-8 sm:py-24 lg:grid-cols-[1.1fr_1fr] lg:items-center">
            <div className="flex flex-col items-start gap-6 text-left">
              <span className="text-sm font-medium text-primary">Atendimento no WhatsApp com IA</span>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-5xl">
                Sua IA responde no WhatsApp enquanto você cuida do resto do negócio
              </h1>
              <p className="max-w-xl text-balance text-muted-foreground sm:text-lg">
                A Hosthub conecta um agente de IA treinado no seu negócio ao WhatsApp: responde clientes 24/7, sabe
                quando chamar um humano e nunca esquece o que você já configurou.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Button size="lg" asChild>
                  <Link href="/login">Criar minha conta</Link>
                </Button>
                <Button variant="outline" size="lg" asChild>
                  <a href="#como-funciona">Ver como funciona</a>
                </Button>
              </div>
            </div>

            <div className="w-full">
              <p className="mb-2 text-center text-xs font-medium text-muted-foreground">
                Converse com o agente de demonstração agora — sem cadastro
              </p>
              <DemoChatWidget />
            </div>
          </div>
        </section>

        <section className="px-4 py-16 sm:px-8">
          <div className="mx-auto max-w-5xl">
            <h2 className="text-center text-2xl font-semibold sm:text-3xl">O que você monta com a Hosthub</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:auto-rows-fr lg:grid-cols-4">
              {PILLARS.map((pillar) => (
                <Card key={pillar.title} className={cn("flex flex-col", pillar.span)}>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-2">
                      <pillar.icon className="size-6 text-primary" />
                      <Badge variant="secondary" className="shrink-0 text-[10px]">
                        {pillar.tier}
                      </Badge>
                    </div>
                    <CardTitle>{pillar.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{pillar.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section id="como-funciona" className="bg-muted/30 px-4 py-16 sm:px-8">
          <div className="mx-auto max-w-5xl">
            <h2 className="text-center text-2xl font-semibold sm:text-3xl">Como funciona</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {HOW_IT_WORKS_STEPS.map((step, index) => (
                <Card key={step.title}>
                  <CardHeader>
                    <span className="flex size-8 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                      {index + 1}
                    </span>
                    <CardTitle>{step.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{step.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="border-t px-4 py-16 text-center sm:px-8 sm:py-20">
          <div className="mx-auto flex max-w-2xl flex-col items-center gap-4">
            <h2 className="text-2xl font-semibold sm:text-3xl">Pronto para colocar sua IA pra atender?</h2>
            <p className="text-muted-foreground">
              Configure o agente com sua base de conhecimento em minutos e conecte ao WhatsApp da sua empresa — o
              teste que você acabou de fazer lá em cima já é o produto de verdade.
            </p>
            <Button size="lg" asChild>
              <Link href="/login">Criar minha conta</Link>
            </Button>
          </div>
        </section>
      </main>

      <footer className="flex flex-col items-center justify-between gap-4 border-t px-4 py-6 sm:flex-row sm:px-8">
        <BrandLockup size="sm" />
        <p className="text-sm text-muted-foreground">© 2026 Hosthub</p>
        <Link href="/login" className="text-sm text-muted-foreground hover:text-foreground">
          Entrar
        </Link>
      </footer>
    </div>
  );
}
