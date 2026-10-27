"""Provider do Google Gemini (AI Studio). Modelo default: gemini-3.5-flash-lite."""
from __future__ import annotations

import base64
from typing import Any

import httpx
from loguru import logger

from app.config import settings
from app.llm.client import BaseLLMClient, Completion, LLMError, Midia


class GeminiProvider(BaseLLMClient):
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.chave("gemini")
        self.model = model or settings.llm_model_name
        self.base_url = settings.llm_api_url.rstrip("/")
        if not self.api_key:
            raise LLMError("LLM_API_KEY não configurada.")

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        schema: dict[str, Any] | None = None,
        midia: Midia | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Completion:
        url = f"{self.base_url}/models/{self.model}:generateContent"
        partes: list[dict[str, Any]] = [{"text": prompt}]
        if midia:
            mime, dados = midia
            partes.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(dados).decode()}})
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": partes}],
            # JSON estruturado + temperatura zero: extração, não criatividade.
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
            },
        }
        if schema:
            payload["generationConfig"]["responseJsonSchema"] = schema
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        logger.info(
            "LLM call feature={} model={} prompt_chars={}",
            (metadata or {}).get("feature", "unknown"),
            self.model,
            len(prompt),
        )
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"Gemini retornou HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha de rede ao chamar o Gemini: {exc}") from exc

        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Resposta do Gemini em formato inesperado.") from exc
        if not text:
            raise LLMError("Gemini retornou uma resposta vazia.")

        usage = data.get("usageMetadata") or {}
        return Completion(
            texto=text,
            tokens_entrada=int(usage.get("promptTokenCount", 0)),
            tokens_saida=int(usage.get("candidatesTokenCount", 0)),
        )
