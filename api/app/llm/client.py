"""Abstração de LLM: interface única + seleção de provider por variável de ambiente.

Adaptado do Finance AI. Mesmo contrato: se o provider remoto falhar, o fallback
determinístico responde — a aplicação nunca fica sem resposta por causa da IA.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from loguru import logger

from app.config import settings


class LLMError(RuntimeError):
    """Falha ao gerar texto com o provider remoto."""


#: Anexo binário (mime, bytes), ex.: áudio gravado no navegador.
Midia = tuple[str, bytes]


@dataclass
class Completion:
    texto: str
    tokens_entrada: int = 0
    tokens_saida: int = 0


@dataclass
class Resultado:
    completion: Completion
    provider: str
    model: str
    offline: bool
    motivo: str = ""


class BaseLLMClient(ABC):
    """Contrato mínimo de um provider de LLM."""

    name: str = "base"
    model: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        schema: dict[str, Any] | None = None,
        midia: Midia | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Completion:
        """`schema`: JSON Schema da resposta (saída estruturada). `midia`: anexo, ex. áudio."""
        raise NotImplementedError


class LLMClient:
    def __init__(
        self,
        provider: BaseLLMClient,
        fallback: BaseLLMClient | None = None,
        *,
        offline: bool = False,
        motivo: str = "",
    ) -> None:
        self._provider = provider
        self._fallback = fallback
        self._offline = offline
        self._motivo = motivo

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._provider.model

    def run(
        self,
        prompt: str,
        *,
        system: str = "",
        schema: dict[str, Any] | None = None,
        midia: Midia | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Resultado:
        try:
            completion = self._provider.generate(
                prompt, system=system, schema=schema, midia=midia, metadata=metadata
            )
            return Resultado(
                completion, self._provider.name, self._provider.model, self._offline, self._motivo
            )
        except Exception as exc:  # noqa: BLE001 - qualquer falha vira degradação, não erro 500
            logger.warning("LLM {} falhou ({}); usando fallback local.", self._provider.name, exc)
            if self._fallback is None:
                raise LLMError(str(exc)) from exc
            completion = self._fallback.generate(
                prompt, system=system, schema=schema, midia=midia, metadata=metadata
            )
            return Resultado(
                completion, self._fallback.name, self._fallback.model, True, str(exc)[:200]
            )


def build_client(fallback: BaseLLMClient | None = None) -> LLMClient:
    """Fábrica: escolhe o provider por `LLM_PROVIDER` e pelas chaves disponíveis.

    `fallback`: provider determinístico da feature (padrão: extrator de itens offline).
    """
    from app.llm.providers.offline import OfflineProvider

    fallback = fallback or OfflineProvider()
    provider = settings.provider_efetivo

    if provider == "gemini":
        from app.llm.providers.gemini import GeminiProvider

        return LLMClient(GeminiProvider(), fallback=fallback)
    if provider == "openai":
        from app.llm.providers.openai import OpenAIProvider

        return LLMClient(OpenAIProvider(), fallback=fallback)

    if settings.llm_provider.lower() not in {"gemini", "openai", "offline"}:
        logger.warning("LLM_PROVIDER desconhecido: {}. Usando fallback local.", settings.llm_provider)
    return LLMClient(fallback, offline=True, motivo="Nenhuma chave de LLM configurada.")
