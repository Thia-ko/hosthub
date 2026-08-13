from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

SYSTEM_PROMPT = (
    "Voce e um editor de prompts de agentes de IA de atendimento. Dado o prompt atual de um agente e uma "
    "instrucao de alteracao, responda APENAS com o texto completo do novo prompt, incorporando a alteracao "
    "pedida. Nao inclua comentarios, explicacoes ou marcacao de codigo, apenas o prompt final."
)


class AiAssistProvider(ABC):
    @abstractmethod
    async def suggest(self, current_prompt: str, instruction: str) -> tuple[str, int, int]:
        """Returns (new_prompt, prompt_tokens, completion_tokens)."""


class OpenAiCompatibleProvider(AiAssistProvider):
    async def suggest(self, current_prompt: str, instruction: str) -> tuple[str, int, int]:
        async with httpx.AsyncClient(base_url=settings.AI_ASSIST_BASE_URL, timeout=60) as client:
            response = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.AI_ASSIST_API_KEY}"},
                json={
                    "model": settings.AI_ASSIST_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": f"Prompt atual:\n{current_prompt}\n\nInstrucao:\n{instruction}",
                        },
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
        new_prompt = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        return new_prompt, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def get_ai_assist_provider() -> AiAssistProvider:
    return OpenAiCompatibleProvider()
