"""Proteções para o site público: limite por IP nas rotas que usam IA.

Em memória (some ao reiniciar a API), o suficiente para uma demo exposta na internet:
impede que um visitante (ou robô) esgote a cota gratuita do Gemini em minutos.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings

#: Rotas (POST) que podem chamar o LLM.
ROTAS_COM_IA = ("/demandas/extrair", "/ofertas/extrair", "/ops/relatos")
_JANELA_S = 60.0

_acessos: dict[str, deque[float]] = defaultdict(deque)


def ip_do_cliente(request: Request) -> str:
    """IP real do visitante, no X-Forwarded-For posto pelo Tailscale Funnel.

    Vale o ÚLTIMO valor: é o que o proxy acrescentou. Os anteriores vêm do próprio visitante
    e podem ser inventados (o Next repassa o cabeçalho sem mexer).
    """
    encaminhado = request.headers.get("x-forwarded-for", "")
    if encaminhado:
        return encaminhado.split(",")[-1].strip()
    return request.client.host if request.client else "desconhecido"


class LimiteIA(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "POST" and request.url.path.startswith(ROTAS_COM_IA):
            agora = time.monotonic()
            fila = _acessos[ip_do_cliente(request)]
            while fila and agora - fila[0] > _JANELA_S:
                fila.popleft()
            if len(fila) >= settings.limite_ia_por_minuto:
                espera = int(_JANELA_S - (agora - fila[0])) + 1
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Muitas mensagens seguidas. Tente de novo em {espera} s."},
                    headers={"Retry-After": str(espera)},
                )
            fila.append(agora)
        return await call_next(request)


def limpar() -> None:
    _acessos.clear()
