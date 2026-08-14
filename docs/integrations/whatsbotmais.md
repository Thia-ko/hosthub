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

O mesmo endpoint de webhook por conexao ("Webhooks | Triggers" no painel deles) despacha **4
formatos de evento diferentes** — confirmado pela doc antiga
([`webhook`](https://help.whaticket-saas.com/webhook)) e por um payload real de producao (mais
novo que o exemplo da doc, formato "API Oficial" com ticket completo aninhado):

1. **Mensagem de cliente** — o unico que o HostHub responde. Payload real:
   ```json
   {
     "mensagem": {
       "id": 8824203, "fromMe": false, "body": "texto da mensagem",
       "mediaType": "conversation",
       "contact": {"number": "557991358293", "name": "..."}
     },
     "sender": "557991358293",
     "fromMe": false,
     "token_origin": "AbCdEfGhIjKlMnOp",
     "ticket": {...}, "ticketData": {...}
   }
   ```
   - `mensagem.mediaType == "conversation"` = texto puro.
   - `mensagem.mediaType` em `"audio"`/`"ptt"` = audio: o HostHub baixa `mensagem.mediaUrl`,
     transcreve via `AI_ASSIST_TRANSCRIBE_MODEL` (endpoint `/audio/transcriptions`, padrao
     Whisper) e responde ao texto transcrito.
   - `mensagem.mediaType == "image"` = imagem: o HostHub manda `mensagem.mediaUrl` direto pro
     modelo de chat como conteudo multimodal (exige `AI_ASSIST_MODEL` com suporte a visao, ex:
     `gpt-4o-mini` ja suporta). A legenda (`mensagem.body`), se houver, vai junto como texto.
   - **[INFERENCE]** Os valores `audio`/`ptt`/`image` acima ainda NAO foram confirmados contra um
     payload real de audio/imagem do WhatsBotMais (so temos o exemplo real de texto, com
     `mediaType: "conversation"`). Foram inferidos por analogia com o campo `type` do webhook
     nativo da Meta Cloud API, que o WhatsBotMais empacota para conexoes "API Oficial". Validar com
     uma mensagem real de audio e de imagem apos o deploy; se os valores reais divergirem, ajustar
     `_AUDIO_MEDIA_TYPES`/`_IMAGE_MEDIA_TYPES` em `whatsapp_channel.py`.
   - Outros valores (`video`, `document`, `sticker`, `location`, `vcard`, `contact`, ...) = midia
     sem pipeline de resposta ainda — o HostHub loga o evento e nao responde.
   - `fromMe: true` (no nivel raiz OU dentro de `mensagem`) = eco da propria mensagem enviada
     (inclusive pelo proprio HostHub) — nunca responder.
   - Pode chegar embrulhado no formato de item do n8n (`{headers, body, query, ...}`), com o
     payload real dentro de `body`. O parser desembrulha automaticamente.
2. **TAGS** — `{"action": "tag-sync", "tags": {...}, "contact": {...}}`. Sem chave `mensagem`.
3. **STATUS DO TICKET** — `{"sender", "acao": "open"|"closed", "ticketData": {...}}`. Sem `mensagem`.
4. **ARQUIVOS enviados/recebidos** — `{"acao": "fila-data", "mediaFolder", "mediaName", ...}`. Sem
   `mensagem` como objeto com `body`.

O parser (`apps/api/app/services/whatsapp_channel.py::_parse_whatsbotmais_payload`) so reconhece o
formato 1 (exige `mensagem` como dict com `body` de texto) — os outros 3 sao ignorados por
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
