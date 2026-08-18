# WhatsBotMais (Whaticket SaaS) — contrato de integracao

O provedor de WhatsApp de todos os clientes atuais do HostHub e a plataforma **WhatsBotMais**,
um white-label do **Whaticket SaaS** (`help.whaticket-saas.com`). Anotacoes aqui sao verificadas
contra a documentacao oficial e/ou payloads reais de producao — nao sao suposicao.

## Enviar mensagem (resposta do HostHub para o cliente)

Confirmado contra a doc oficial ([`mensagem-hub-texto`](https://help.whaticket-saas.com/mensagem-hub-texto))
e contra um curl real fornecido pelo dono da plataforma — os dois batem exatamente.

```
POST {WHATSBOTMAIS_API_BASE_URL}/api/messages/sendOfficialData
Authorization: Bearer {token}
Content-Type: application/json

{"number": "5511999999999", "text": "..."}
```

- Resposta de sucesso: `{"response": {"from","to","contents","id","direction":"OUT"}}`. Sem flag de
  erro no corpo — validar so pelo status HTTP (2xx).
- `token` = o `token_origin` que vem em cada evento de mensagem recebida (ver abaixo). Nao precisa
  configurar credencial por instancia no HostHub: o token certo ja chega junto com cada mensagem.
- Implementado em `apps/api/app/services/whatsapp_channel.py::send_whatsbotmais_reply`.

## Receber mensagem (webhook por conexao)

O mesmo endpoint de webhook por conexao ("Webhooks | Triggers" no painel deles) despacha varios
`acao` diferentes. **Verificado em 18/08/2026** contra uma bateria real de mensagens (texto,
imagem, audio, documento/PDF e video) enviadas a uma conexao WhatsBotMais em producao e
capturadas em `WebhookEvent.payload_json` — o que segue e fato observado, nao mais inferencia.

Cada mensagem do cliente dispara **dois webhooks quase simultaneos** com o mesmo conteudo em
formatos diferentes:

1. **`acao: "queue_webhook_from_internal"`** (ou `"from_internal"` em tickets mais antigos) —
   `mensagem` e um **dict** com `body`/`mediaType`/`mediaUrl`. **Este e o unico formato que o
   parser reconhece e responde.** Payload real (imagem):
   ```json
   {
     "acao": "queue_webhook_from_internal",
     "mensagem": {
       "id": 11047610, "fromMe": false,
       "body": "f3c0f45d-...-3EB0D8DFC5B7241B88EB80.jpg",
       "mediaType": "image",
       "mediaUrl": "https://object.sp2.eveo.com.br/.../f3c0f45d-....jpg"
     },
     "sender": "557991358293",
     "fromMe": false,
     "token_origin": "660d3e5ab0f1009004f",
     "ticket": {...}, "ticketData": {...}
   }
   ```
   - `mensagem.mediaType == "conversation"` = texto puro (`mensagem.body` = o texto real do
     cliente). **Confirmado.**
   - `mensagem.mediaType == "audio"` = audio. **Confirmado** (valor real observado, igual ao
     inferido). `mensagem.body` vem com o *nome do arquivo*, nao com texto — o texto de fato usado
     na resposta e a transcricao de `mensagem.mediaUrl` via Whisper.
   - `mensagem.mediaType == "image"` = imagem. **Confirmado**, mesmo tratamento.
   - `mensagem.mediaType == "application"` = documento/PDF. **Achado novo, nao estava na doc
     antiga** (o valor chutado la era `"document"`, que nunca aparece na pratica para uma conexao
     WhatsBotMais/Baileys). Sem `"application"` em `_UNSUPPORTED_MEDIA_TYPES`, o parser caia no
     fallback de texto puro usando `mensagem.body` — que para documento e o **nome do arquivo**,
     nao uma mensagem do cliente — e o pipeline de auto-resposta responderia a um nome de arquivo
     aleatorio. **Corrigido** em `_UNSUPPORTED_MEDIA_TYPES` (`whatsapp_channel.py`); regressao
     coberta em `tests/test_whatsapp_channel.py::test_whatsbotmais_document_attachment_does_not_leak_filename_as_text`.
   - `mensagem.mediaType == "video"` = sem pipeline de resposta. **Confirmado**: nenhuma
     `ConversationMessage` e criada, o evento so e logado.
   - `fromMe: true` (no nivel raiz OU dentro de `mensagem`) = eco da propria mensagem enviada
     (inclusive pelo proprio HostHub) — nunca responder.
   - Pode chegar embrulhado no formato de item do n8n (`{headers, body, query, ...}`), com o
     payload real dentro de `body`. O parser desembrulha automaticamente.
   - **Achado**: em mensagens de abertura de ticket (`acao: "start"`), `token_origin` pode vir
     `null` — a primeira mensagem de uma conversa nova nao gera auto-resposta por falta de
     credencial; mensagens seguintes do mesmo ticket ja vem com `token_origin` preenchido.
2. **`acao: "queue_webhook"`** — `mensagem` e uma **lista**: `[{"type": "text"|"image"|"audio"|
   "video"|"document", "text"/"fileUrl", "fileMimeType", "originalData": {...payload cru do
   WhatsApp/Baileys}}]`. Chega para a mesma mensagem do formato 1, alguns milissegundos antes ou
   depois. **Ignorado por construcao** (`mensagem` nao e dict) — nao precisa de tratamento
   especial, mas explica por que cada mensagem real gera 2 linhas em `WebhookEvent`.
3. **TAGS** — `{"action": "tag-sync", "tags": {...}, "contact": {...}}`. Sem chave `mensagem`.
4. **STATUS DO TICKET** — `{"sender", "acao": "open"|"closed", "ticketData": {...}}`. Sem
   `mensagem`. **Confirmado** em producao (`acao: "closed"` observado).
5. **ARQUIVOS enviados/recebidos** — `{"acao": "fila-data", "mediaFolder", "mediaName", ...}`. Sem
   `mensagem` como objeto com `body`.

O parser (`apps/api/app/services/whatsapp_channel.py::_parse_whatsbotmais_payload`) so reconhece o
formato 1 (exige `mensagem` como dict com `body` de texto) — os outros sao ignorados por
construcao, sem precisar enumerar `acao`/`event`.

## Webhook administrativo (fora do escopo do HostHub)

Eventos de conexao (`connected`/`disconnected`) tem formato totalmente diferente e vao para uma URL
global separada (Configuracoes -> Opcoes -> Configuracoes Globais), nao para o webhook por
instancia que o HostHub usa: `{"whatsappId", "companyId", "event": "200", "status": "connected",
"channel": "whatsapp"}`. Nao processado pelo HostHub.

## Onde ver a doc completa

- Changelog: https://help.whaticket-saas.com/atualizacoes-and-versao
- Indice de APIs: https://help.whaticket-saas.com/api-sistema-or-baileys-or-oficial
- HUB Omnichannel (Instagram/Facebook/Telegram/E-mail, fora do escopo atual — todos os clientes
  usam WhatsApp API Oficial direto): https://help.whaticket-saas.com/hub-omnichannel

## Notas de changelog relevantes (para acompanhar, nao bloqueante)

- Ate pelo menos mar/2025: fechamento automatico de ticket via API Oficial estava temporariamente
  bloqueado do lado do WhatsBotMais.
- Reformulacao do processo de abertura/reabertura de ticket via API Oficial estava em andamento em
  abr/2025 (ainda sem check de conclusao no changelog publico).
- **Verificado em 14/08/2026**: o changelog publico
  ([`atualizacoes-and-versao`](https://help.whaticket-saas.com/atualizacoes-and-versao)) só
  detalha entradas ate 25/05/2025 — a partir de 01/05/2025 o WhatsBotMais moveu o detalhamento
  de atualizacoes para uma plataforma de feedback privada, entao **nao da para confirmar por
  doc publica** se o bloqueio de fechamento automatico foi levantado ou se a reformulacao de
  abertura/reabertura terminou. Continua valendo: nao implementar gerenciamento automatico de
  status de ticket sem testar contra a conta de producao primeiro (ou abrir chamado com o
  suporte WhatsBotMais perguntando o estado atual).
- Existe um endpoint documentado de fechamento **manual** de ticket via API Oficial (HUB),
  separado do fechamento automatico por inatividade:
  [`Encerrar Atendimento`](https://help.whaticket-saas.com/encerrar-atendimento) —
  `POST {BACKEND_URL}/api/messages/finish` com `{"companyId", "ticketId"}` e o mesmo Bearer
  token da conexao. Nao usado pelo HostHub hoje; e a rota candidata caso decidam fechar o ticket
  manualmente apos o agente responder (precisa de `ticketId`, que hoje so chega no payload de
  webhook via `ticket.id`/`ticketData` — o parser atual em `whatsapp_channel.py` nao extrai
  esse campo, so `sender`/`token_origin`/`mensagem`).
