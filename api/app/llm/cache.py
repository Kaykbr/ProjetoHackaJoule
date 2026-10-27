"""Cache de respostas já validadas: a mesma mensagem não paga a IA duas vezes.

Guarda o resultado final (itens já conferidos), não o texto bruto do LLM. A chave inclui o
modelo e a data, porque prazos relativos ("até sexta") dependem do dia. Fica em memória:
some ao reiniciar a API, o que é aceitável para o MVP.
"""
from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Any

from app.config import settings


class CacheRespostas:
    def __init__(self, max_itens: int = 256, ttl_s: float = 6 * 3600) -> None:
        self._dados: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._max = max_itens
        self._ttl = ttl_s

    @staticmethod
    def chave(*partes: str) -> str:
        return hashlib.sha256("\x1f".join(partes).encode()).hexdigest()

    def obter(self, chave: str) -> Any | None:
        if not settings.cache_ia_enabled:
            return None
        achado = self._dados.get(chave)
        if achado is None:
            return None
        expira, valor = achado
        if time.monotonic() > expira:
            del self._dados[chave]
            return None
        self._dados.move_to_end(chave)
        return valor

    def guardar(self, chave: str, valor: Any) -> None:
        if not settings.cache_ia_enabled:
            return
        self._dados[chave] = (time.monotonic() + self._ttl, valor)
        self._dados.move_to_end(chave)
        while len(self._dados) > self._max:
            self._dados.popitem(last=False)

    def limpar(self) -> None:
        self._dados.clear()


respostas = CacheRespostas()
