import Link from "next/link";
import { Cable, Gauge, Megaphone, MessagesSquare, Star, UserCheck, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BrandLockup } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { DemoChatWidget } from "@/components/demo-chat-widget";

const IMPACT_ITEMS: { icon: LucideIcon; title: string; description: string }[] = [
  {
    icon: MessagesSquare,
    title: "Resposta automática 24/7",
    description:
      "O agente responde no WhatsApp assim que a mensagem chega, com base no prompt e nos arquivos de conhecimento que você configurar — sem depender de alguém estar online.",
  },
  {
    icon: UserCheck,
    title: "Sabe quando chamar um humano",
    description:
      "Reclamações, reembolsos ou perguntas fora do escopo são escalonadas automaticamente para um atendente, sem deixar o cliente sem resposta.",
  },
  {
    icon: Gauge,
    title: "Resolução medida, não achismo",
    description:
      "O dashboard mostra quantos atendimentos a IA resolveu sozinha, taxa de resolução e horas estimadas economizadas da equipe.",
  },
  {
    icon: Star,
    title: "Satisfação pós-atendimento",
    description: "Pesquisas de CSAT automáticas depois de cada conversa mostram a nota real dos seus clientes.",
  },
  {
    icon: Megaphone,
    title: "Campanhas dentro da janela do WhatsApp",
    description:
      "Disparos em massa respeitam a janela de 24h da API do WhatsApp automaticamente, sem risco de bloqueio.",
  },
  {
    icon: Cable,
    title: "Conecta no seu WhatsApp de verdade",
    description: "Integração com WhatsBotMais, Evolution API ou API oficial da Meta — você escolhe.",
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
        <section className="flex flex-col items-center gap-6 px-4 py-16 text-center sm:px-8 sm:py-24">
          <span className="text-sm font-medium text-primary">Atendimento no WhatsApp com IA</span>
          <h1 className="max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">
            Sua IA responde no WhatsApp enquanto você cuida do resto do negócio
          </h1>
          <p className="max-w-2xl text-balance text-muted-foreground sm:text-lg">
            A Hosthub conecta um agente de IA treinado no seu negócio ao WhatsApp: responde clientes 24/7, sabe
            quando chamar um humano e nunca esquece o que você já configurou.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button size="lg" asChild>
              <a href="#demo">Testar demonstração grátis</a>
            </Button>
            <Button variant="outline" size="lg" asChild>
              <Link href="/login">Já sou cliente — Entrar</Link>
            </Button>
          </div>
        </section>

        <section className="px-4 py-16 sm:px-8">
          <div className="mx-auto grid max-w-5xl gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {IMPACT_ITEMS.map((item) => (
              <Card key={item.title}>
                <CardHeader>
                  <item.icon className="size-6 text-primary" />
                  <CardTitle>{item.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{item.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="bg-muted/30 px-4 py-16 sm:px-8">
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

        <section id="demo" className="px-4 py-16 sm:px-8">
          <div className="mx-auto flex max-w-2xl flex-col items-center gap-4 text-center">
            <h2 className="text-2xl font-semibold sm:text-3xl">Veja a IA respondendo antes de decidir</h2>
            <p className="text-muted-foreground">
              Converse com o agente de demonstração da Barbearia Vintage (negócio fictício) e veja exatamente como
              seus clientes seriam atendidos. Limite de 6 mensagens por sessão.
            </p>
          </div>
          <div className="mx-auto mt-8 max-w-2xl">
            <DemoChatWidget />
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
