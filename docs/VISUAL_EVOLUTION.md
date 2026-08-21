# Evolução Visual do HostHub

Memorial de mudanças visuais relevantes do produto, mantido como parte do fluxo de
trabalho normal (não um documento retroativo/pontual). Toda alteração visual relevante
(layout, hierarquia, motion, componentes de UI) deve:

1. Gerar um snapshot com `scripts/take-snapshot.ts` (antes de mudar, se a tela já existir
   no histórico, e depois de aplicar a mudança).
2. Ganhar uma entrada nova na seção [Histórico de mudanças](#histórico-de-mudanças) deste
   arquivo, com uma explicação breve do que mudou e os caminhos dos prints.

## Protocolo de snapshot

Script: [`scripts/take-snapshot.ts`](../scripts/take-snapshot.ts). Requer o stack rodando
(`docker compose up`, ou os containers `hosthub-web-1`/`hosthub-api-1`/`hosthub-proxy-1`
já de pé) e as dependências de tooling instaladas na raiz do repo (`npm install`).

```bash
# da raiz do repo
npm run snapshot -- <label> <path> [opcoes]

# exemplos usados neste memorial
npm run snapshot -- client-dashboard /app --email=<email> --password=<senha>
npm run snapshot -- admin-dashboard /admin --email=<email> --password=<senha>
```

- `<label>`: identifica a tela (`client-dashboard`, `admin-instances`, ...). Cada label
  tem sua própria pasta em `docs/screenshots/<label>/`.
- `<path>`: rota a capturar (relativa a `--base`, padrão `http://localhost:8888`, o proxy
  Caddy — **não** a porta 3000 do container `web` direto, que não resolve `/api/*`).
- `--email`/`--password`: login automático via `POST /api/v1/auth/login` antes de
  navegar, necessário para rotas protegidas (`/app`, `/admin`).
- Cada execução salva um novo arquivo `docs/screenshots/<label>/<timestamp>.png` e nunca
  sobrescreve os anteriores — `ls docs/screenshots/<label>/` dá o histórico daquela tela
  em ordem cronológica. O script imprime o print anterior (se existir, prefixado
  `PREVIOUS:`) e o novo (última linha), para montar o par antes/depois no momento do commit.

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

**Prints:**

> Este é o primeiro registro do protocolo de snapshot — não existe um "antes" persistido
> desta mudança (o protocolo nasceu junto com ela). A partir daqui, toda entrada nova
> deste memorial deve incluir o par antes/depois real.

- Depois — dashboard do cliente (`/app`):
  [`docs/screenshots/client-dashboard/2026-08-21T06-01-37-628Z.png`](screenshots/client-dashboard/2026-08-21T06-01-37-628Z.png)
- Depois — dashboard do admin (`/admin`):
  [`docs/screenshots/admin-dashboard/2026-08-21T06-01-44-529Z.png`](screenshots/admin-dashboard/2026-08-21T06-01-44-529Z.png)
