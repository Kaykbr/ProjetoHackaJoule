"""Fallback determinístico: extrai os itens localmente, sem chamar nenhuma API.

Usado quando não há `LLM_API_KEY` ou quando o provider remoto falha. Responde no mesmo
formato JSON pedido ao LLM, então o resto do sistema não sabe a diferença.
"""
from __future__ import annotations

import json
from typing import Any

from app.llm.client import BaseLLMClient, Completion, Midia
from app.services.parser_local import extrair_itens


class OfflineProvider(BaseLLMClient):
    name = "offline"
    model = "regras-locais"

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        schema: dict[str, Any] | None = None,
        midia: Midia | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Completion:
        texto = (metadata or {}).get("texto", "")
        return Completion(texto=json.dumps({"itens": extrair_itens(texto)}, ensure_ascii=False))
