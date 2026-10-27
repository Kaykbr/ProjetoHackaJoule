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
    """IP real do visitante, contado a partir do FIM do X-Forwarded-For.

    Cada proxy confiável acrescenta um IP no fim; os valores antes deles vêm do próprio visitante
    e podem ser inventados. Com `PROXIES_CONFIAVEIS=N`, o visitante é o N-ésimo a partir do fim
    (1 com o Tailscale Funnel; 2 com Vercel + Render).
    """
    encaminhado = [ip.strip() for ip in request.headers.get("x-forwarded-for", "").split(",") if ip.strip()]
    if encaminhado:
        return encaminhado[-min(max(1, settings.proxies_confiaveis), len(encaminhado))]
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
