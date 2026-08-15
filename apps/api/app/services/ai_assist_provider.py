import asyncio
from abc import ABC, abstractmethod

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.ai_settings import get_effective_ai_settings
from app.utils.json_utils import safe_parse_json

SYSTEM_PROMPT = (
    "Voce e um editor de prompts de agentes de IA de atendimento. Dado o prompt atual de um agente e uma "
    "instrucao de alteracao, responda APENAS com o texto completo do novo prompt, incorporando a alteracao "
    "pedida.\n"
    "Regras:\n"
    "1. Faca APENAS a alteracao pedida - nada mais, nada menos.\n"
    "2. NUNCA remova informacoes factuais existentes (nome do negocio, produtos, precos, horarios, FAQ, "
    "politicas) a menos que a instrucao peca explicitamente para remove-las.\n"
    "3. NUNCA reestruture, reorganize ou reescreva o prompt inteiro, a menos que a instrucao peca "
    "EXPLICITAMENTE (ex: 'reescreva tudo', 'reestruture o prompt').\n"
    "4. Preserve exatamente a formatacao, secoes, titulos e ordem do prompt original - altere so o trecho "
    "necessario.\n"
    "5. Se a instrucao for ambigua, faca a alteracao minima mais razoavel.\n"
    "Nao inclua comentarios, explicacoes ou marcacao de codigo, apenas o prompt final."
)


class AiAssistProvider(ABC):
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether this provider has a usable API key (from the admin panel or env var)."""

    @abstractmethod
    async def suggest(self, current_prompt: str, instruction: str) -> tuple[str, int, int]:
        """Returns (new_prompt, prompt_tokens, completion_tokens)."""

    @abstractmethod
    async def reply(
        self, system_prompt: str, history: list[dict], user_message: str, image_url: str | None = None
    ) -> tuple[str, int, int]:
        """Roleplays the agent for a sandbox test or a real customer message. When `image_url` is
        set, the message is sent as multimodal content (requires a vision-capable model).
        Returns (reply, prompt_tokens, completion_tokens)."""

    @abstractmethod
    async def transcribe(self, audio_url: str) -> str:
        """Downloads the audio at `audio_url` and returns its transcribed text."""

    @abstractmethod
    async def extract_json(self, system_prompt: str, user_content: str, temperature: float = 0.2) -> tuple[dict, int, int]:
        """Sends a JSON-mode chat completion and returns (parsed_object, prompt_tokens, completion_tokens).
        Raises ValueError if the response isn't valid/extractable JSON."""


class OpenAiCompatibleProvider(AiAssistProvider):
    def __init__(self, api_key: str, base_url: str, model: str, transcribe_model: str):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._transcribe_model = transcribe_model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def _chat_completion(self, messages: list[dict]) -> tuple[str, int, int]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=60) as client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "messages": messages},
            )
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        return content, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    async def suggest(self, current_prompt: str, instruction: str) -> tuple[str, int, int]:
        return await self._chat_completion(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Prompt atual:\n{current_prompt}\n\nInstrucao:\n{instruction}",
                },
            ]
        )

    async def reply(
        self, system_prompt: str, history: list[dict], user_message: str, image_url: str | None = None
    ) -> tuple[str, int, int]:
        user_content: str | list[dict] = user_message
        if image_url:
            user_content = [
                {"type": "text", "text": user_message or "Cliente enviou uma imagem sem legenda."},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": user_content}]
        return await self._chat_completion(messages)

    async def transcribe(self, audio_url: str) -> str:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            audio_response = await client.get(audio_url)
            audio_response.raise_for_status()

        filename = audio_url.rsplit("/", 1)[-1].split("?", 1)[0] or "audio.ogg"
        content_type = audio_response.headers.get("content-type", "application/octet-stream")

        async with httpx.AsyncClient(base_url=self._base_url, timeout=60) as client:
            response = await client.post(
                "/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                data={"model": self._transcribe_model},
                files={"file": (filename, audio_response.content, content_type)},
            )
            response.raise_for_status()
            data = response.json()

        text = data.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Transcricao de audio veio vazia")
        return text.strip()

    async def extract_json(
        self, system_prompt: str, user_content: str, temperature: float = 0.2
    ) -> tuple[dict, int, int]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        for attempt in range(3):
            async with httpx.AsyncClient(base_url=self._base_url, timeout=60) as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                        "temperature": temperature,
                    },
                )
            if response.status_code == 429 and attempt < 2:
                await asyncio.sleep(2**attempt)
                continue
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            parsed = safe_parse_json(content)
            if parsed is None:
                raise ValueError("Resposta do provedor de IA nao e um JSON valido")
            return parsed, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


async def get_ai_assist_provider(db: AsyncSession = Depends(get_db)) -> AiAssistProvider:
    effective = await get_effective_ai_settings(db)
    return OpenAiCompatibleProvider(effective.api_key, effective.base_url, effective.model, effective.transcribe_model)
