# Evolução Visual do HostHub

Registro em texto das mudanças visuais relevantes do produto (layout, hierarquia,
motion, componentes de UI): o que mudou, por quê e em qual issue. Sem automação de
captura de tela — este arquivo é mantido manualmente a cada mudança visual relevante,
como parte do fluxo de trabalho normal.

## Bibliotecas visuais (dependências)

| Biblioteca | Versão | Papel |
|---|---|---|
| [Tailwind CSS](https://tailwindcss.com/) | `^4` | Utilitários de estilo; tokens de tema (cores OKLCH, `--ease-brand`) definidos em `app/globals.css` via `@theme inline`. |
| [radix-ui](https://www.radix-ui.com/) | `^1.6.7` | Primitivos acessíveis (Dialog, Select, DropdownMenu, Sheet, Avatar, Slot) por trás dos componentes shadcn em `components/ui/`. |
| [shadcn](https://ui.shadcn.com/) (CLI) | `^4.17.0` | Gerador dos componentes base em `components/ui/` (Badge, Button, Card, Dialog, Sheet, Select, DropdownMenu...). |
| [Framer Motion](https://motion.dev/) | `^13.1.1` | Animações de entrada, hover e loop (status badges, header) — curva compartilhada em `lib/motion.ts`, espelhando `--ease-brand`. |
| [class-variance-authority](https://cva.style/) | `^0.7.1` | Variantes de componentes (`badgeVariants`, `buttonVariants`). |
| [tailwind-merge](https://github.com/dcastil/tailwind-merge) | `^3.6.0` | Resolve conflitos de classes Tailwind em `cn()` (`lib/utils.ts`). |
| [tw-animate-css](https://github.com/Wombosvideo/tw-animate-css) | `^1.4.0` | Utilities `animate-in`/`animate-out`/`fade`/`zoom` usadas pelos popovers/menus Radix. |
| [lucide-react](https://lucide.dev/) | `^1.31.0` | Ícones. |
| [next-themes](https://github.com/pacocoursey/next-themes) | `^0.4.6` | Alternância claro/escuro persistida. |
| [Recharts](https://recharts.org/) | `^3.8.0` | Gráficos do dashboard (mensagens por hora, sparklines). |

## Histórico de mudanças

### Milestone 1 — Refatoração da UI do Dashboard (2026-08-21)

Issues: [#11](https://github.com/Thia-ko/hosthub/issues/11) (indicadores de status com
motion), [#12](https://github.com/Thia-ko/hosthub/issues/12) (elevar UI/UX do dashboard).

**O que mudou:**

- **Sidebar limpa:** removido o bloco de branding "Hosthub / Painel do cliente" do topo e
  o cartão de usuário (nome/email/role + botões de tema e "Sair") do rodapé. A sidebar
  agora é exclusivamente navegação.
- **Header contextual:** nova barra persistente no topo da área principal (não na
  sidebar), com saudação dinâmica à esquerda (derivada do item de navegação ativo — ex.:
  "Visão Geral do Hub", "Instancias") e um Profile Dropdown à direita (nome do usuário,
  alternância de tema, "Sair"), construído sobre `DropdownMenu` (Radix) + `Avatar`.
- **Saudação contextual:** o título genérico "Sua IA" do dashboard do cliente virou
  "Bem-vindo de volta, {primeiro nome}", via um `CurrentUserProvider` que compartilha o
  usuário logado com páginas client-side sem round-trip extra.
- **Cards de métricas refinados:** padding interno maior e hierarquia tipográfica mais
  clara (`StatCard` ganhou uma prop `value` com número grande/bold; rótulo virou
  uppercase/sutil), aplicado tanto no dashboard do cliente quanto no do admin.
- **Motion consistente:** indicadores de status ativos com pulso e hover animados
  (Framer Motion + `asChild`/Radix `Slot`), curva de easing compartilhada
  (`lib/motion.ts`, espelha `--ease-brand` de `globals.css`), respeitando
  `prefers-reduced-motion`.

**Verificação:** validado manualmente via browser (login real como cliente e como admin,
desktop e mobile, tema claro/escuro, dropdown/logout) — sem prints anexados a este
registro.
