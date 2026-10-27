"""Provider da OpenAI (Chat Completions com saída estruturada via JSON Schema).

Usado quando `LLM_PROVIDER=openai` ou quando só `OPENAI_API_KEY` está configurada.
Não aceita áudio aqui: a transcrição por voz no MVP é feita pelo navegador ou pelo Gemini.
"""
from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.llm.client import BaseLLMClient, Completion, LLMError, Midia


class OpenAIProvider(BaseLLMClient):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.chave("openai")
        self.model = model or settings.openai_model
        self.base_url = settings.openai_api_url.rstrip("/")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY não configurada.")

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        schema: dict[str, Any] | None = None,
        midia: Midia | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Completion:
        if midia:
            raise LLMError("O provider OpenAI deste MVP não recebe áudio.")
        mensagens = [{"role": "system", "content": system}] if system else []
        mensagens.append({"role": "user", "content": prompt})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": mensagens,
            "temperature": 0,
            "max_tokens": 800,
        }
        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "saida", "schema": schema, "strict": False},
            }
        logger.info(
            "LLM call feature={} model={} prompt_chars={}",
            (metadata or {}).get("feature", "unknown"),
            self.model,
            len(prompt),
        )
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"OpenAI retornou HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha de rede ao chamar a OpenAI: {exc}") from exc

        try:
            texto = (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Resposta da OpenAI em formato inesperado.") from exc
        if not texto:
            raise LLMError("OpenAI retornou uma resposta vazia.")
        uso = data.get("usage") or {}
        return Completion(
            texto=texto,
            tokens_entrada=int(uso.get("prompt_tokens", 0)),
            tokens_saida=int(uso.get("completion_tokens", 0)),
        )
