# Backlog — Evolução da tela de Agente de IA / Prompt

> Registro das ideias levantadas em 2026-08-18. Todos os 7 itens
> implementados em 2026-08-18 (ver notas de status em cada item).

## 1. Demonstração inicial guiada (onboarding)
Passo a passo de apresentação do sistema e das ferramentas quando o usuário
é novo ou o ambiente (instância) é novo. Precisa definir: trigger (primeiro
login? instância recém-criada?), se é dispensável/rejogável, e se cobre só a
tela de prompt ou o admin inteiro.
- **Complexidade**: média-alta (estado de "já viu o tour" por usuário/instância,
  overlay/spotlight sobre elementos reais da UI).
- **Depende de**: nada tecnicamente, mas ganha mais sentido depois das
  abas (#2) e da renomeação (#6) existirem.
- **Status**: ✅ Implementado (`components/onboarding-tour.tsx` +
  `components/app-shell.tsx`). Trigger automático na primeira visita a cada
  seção (admin/app), persistido em `localStorage` (`hosthub:onboarding-seen:*`);
  botão "Tour guiado" no rodapé da sidebar permite rejogar a qualquer momento.
  Cobre os itens de navegação de cada seção com spotlight + tooltip.

## 2. Separar as etapas do prompt em abas
Hoje o modo guiado (`guided-wizard.tsx`) percorre 8 seções em sequência
(Identidade, Tom e Personalidade, Informações do Negócio, Produtos e
Serviços, Políticas, Perguntas Frequentes, Regras de Atendimento, Como
Lidar com Situações Difíceis). Ideia: expor essas seções como abas
navegáveis (em vez de/além do fluxo sequencial atual), permitindo pular
direto para a que precisa editar.
- **Complexidade**: baixa-média — reestrutura navegação interna do
  componente existente, sem novo backend.
- **Arquivo principal**: `apps/web/app/app/prompt/guided-wizard.tsx`.
- **Status**: ✅ Implementado. `GuidedWizard` agora usa `Tabs`/`TabsList`/
  `TabsTrigger` (shadcn) com as 8 seções + "Revisão"; navegação direta por
  clique, mais os botões Voltar/Avançar preservados.

## 3. Mini preview de "cérebro" na aba de dados coletados
Visualização decorativa (não funcional) de um cérebro sendo "energizado"
com informações, na aba onde os dados coletados da IA aparecem — reforço
visual de que o sistema está aprendendo.
- **Complexidade**: média (animação/ilustração, possivelmente SVG ou
  Lottie; precisa achar/definir a aba de "dados coletados" — confirmar
  se já existe ou se é nova).
- **Relacionado a**: #4 (comentários textuais podem viver no mesmo
  componente visual).
- **Status**: ✅ Implementado junto com #4 em `components/ai-brain-preview.tsx`.

## 4. Análise resumida de inteligência da IA + comentários dinâmicos
Resumo de "como está a inteligência da IA" (métricas: volume de dados,
cobertura das 8 seções, última atualização, etc. — a definir) e frases
rotativas tipo "Pensando...", "Adotando novas medidas...", "Conhecimento
nunca é demais!", "Fome de saber". Pode ficar dentro/embaixo do cérebro
de #3.
- **Complexidade**: média — precisa decidir a métrica real por trás do
  "resumo" (não pode ser só decorativo) e o mecanismo de rotação das
  frases (client-side, timer).
- **Depende de**: #3 para o container visual, ou pode ser standalone.
- **Status**: ✅ Implementado (`AiBrainPreview`, usado em
  `app/app/prompt/dados-coletados/view.tsx`). Score 0-100 calculado a partir
  dos contadores reais de `DataReadiness` (conversas, dados extraídos, FAQs,
  padrões); frases rotativas incluem as sugeridas pelo usuário.

## 5. Gerenciador de arquivos para treinar a IA
Upload de arquivos de conhecimento — texto, imagem, vídeo, áudio — com
opção de especificar quando cada arquivo deve ser usado, ou deixar como
default (o agente decide quando usar) e opção de restringir a um caso
específico (uso pontual/singular).
- **Complexidade**: alta — precisa de: storage de arquivos (novo model/
  bucket), pipeline de ingestão diferente por tipo (texto vs. mídia),
  regra de "quando usar" (auto vs. manual vs. caso único) persistida e
  consumida pelo `prompt_generator.py`/pipeline de IA no backend
  (`apps/api`). Maior escopo de todas as ideias listadas.
- **Depende de**: definição de como a IA hoje consome contexto (RAG?
  prompt fixo?) antes de desenhar a solução.
- **Status**: ✅ Implementado (v1). `InstanceKnowledgeFile` (model +
  migration `0018`), upload real via `POST .../knowledge-files`
  (`apps/api/app/api/v1/routers/knowledge_files.py`). Texto e decodificado
  direto; imagem e legendada via `AiAssistProvider.describe_image`
  (multimodal); audio e transcrito via `transcribe_bytes` (Whisper);
  video exige legenda manual (sem pipeline de video). `usage_mode`
  implementa as 3 semanticas pedidas: `auto` (agente sempre usa),
  `manual` + `include_next` (usar so na proxima geracao - "caso
  singular", reseta sozinho apos consumido), `disabled`. O conteudo
  realmente entra no bloco de dados que vira o prompt gerado
  (`prompt_generator.py::_format_collected_data`), verificado lendo o
  bloco montado com um arquivo real. UI: nova secao "Arquivos de
  conhecimento" em `dados-coletados/view.tsx`
  (`components/knowledge-file-manager.tsx`).

## 6. Renomear aba "Prompt" → "Agente de IA"
A aba deixa de representar só o texto do prompt e passa a englobar
configurações da IA como um todo (wizard, arquivos, conexão, etc.).
- **Complexidade**: baixa — troca de label de navegação/rota; conferir
  se `view.tsx` ou algum componente de menu referencia o texto "Prompt"
  em múltiplos lugares (buscar via `lsp references` antes de renomear,
  já que pode ter i18n ou breadcrumb dependente).
- **Depende de**: nada; habilita #2, #5, #7 fazerem sentido sob o mesmo
  guarda-chuva.
- **Status**: ✅ Implementado. Label trocado em `app-shell.tsx` (nav do
  cliente) e `layout-client.tsx` (abas de instância no admin), além do
  `<h1>` e `<title>` da própria página.

## 7. Aba de conexão direta ao WhatsApp (EvolutionAPI + API oficial Meta)
Nova aba de conexão, com botão "Criar Instância" permitindo escolher
entre API oficial da Meta ou EvolutionAPI, mais outras configurações
(a especificar: número, webhook, token, etc.).
- **Complexidade**: alta — integração externa dupla (EvolutionAPI já tem
  precedente em `docs/integrations/whatsbotmais.md`, conferir se dá pra
  reaproveitar padrão; API oficial da Meta exige app review/Business
  verification, tokens de sistema, webhook público). Maior risco/escopo
  junto com #5.
- **Depende de**: decisão de arquitetura (credenciais por instância,
  onde ficam armazenadas, rotacao de token).
- **Status**: ✅ Implementado (v1). Nova aba "Conexao" (instancia admin +
  painel do cliente) com 3 opcoes reais: WhatsBotMais (informativo, sem
  credencial - continua sendo o canal padrao hoje), Evolution API
  (fluxo real de criar instancia + QR code + polling de status contra a
  API Evolution de verdade, corrigido um bug pre-existente no formato do
  body de `sendText`), API Oficial Meta (valida Phone Number ID +
  Access Token com uma chamada real ao Graph API antes de salvar -
  testado ao vivo contra `graph.facebook.com`, retorna 401 real para
  credencial invalida, nada e salvo em caso de falha). Webhook da Meta
  ganhou o handshake de verificacao (`GET` com `hub.challenge`),
  reaproveitando o `webhook_token` existente como verify token - sem
  segredo novo. Endpoints: `apps/api/app/api/v1/routers/
  whatsapp_connection.py`, migration `0017`.

---

### Ordem sugerida de execução (por risco/dependência, não por valor de negócio)
1. #6 Renomear aba "Prompt" → "Agente de IA"
2. #2 Separar etapas em abas
3. #3 + #4 Preview do cérebro e frases dinâmicas (pode virar 1 entrega)
4. #1 Onboarding guiado
5. #5 Gerenciador de arquivos de treino
6. #7 Conexão WhatsApp (EvolutionAPI + Meta oficial)

Todos os 7 itens acima foram implementados em 2026-08-18. Ver notas de
**Status** em cada item para arquivos/decisões específicas.
