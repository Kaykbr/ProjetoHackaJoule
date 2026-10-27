"""Texto do relato → coordenadas.

Ordem: dicionário local de lugares (instantâneo, sem rede) → Nominatim/OpenStreetMap
(limitado à cidade, 1 req/s conforme a política de uso) → centro da cidade.
O dicionário vem primeiro porque cobre os lugares de atuação das ONGs e não depende de rede.
"""
from __future__ import annotations

import asyncio
import re
import time
import unicodedata
from dataclasses import dataclass

import httpx
from loguru import logger

from app.cidades import CIDADE_PADRAO, Cidade, Lugar, obter
from app.config import settings


@dataclass(frozen=True)
class Coordenada:
    fonte: str  # "dicionario" | "nominatim" | "centro"
    consulta: str
    lat: float
    lng: float
    nome: str
    bairro: str


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


_apelidos: dict[str, list[tuple[str, Lugar]]] = {}


def _apelidos_da(cidade: Cidade) -> list[tuple[str, Lugar]]:
    """(apelido normalizado, lugar) da cidade, do apelido mais longo para o mais curto."""
    if cidade.id not in _apelidos:
        _apelidos[cidade.id] = sorted(
            ((a, lugar) for lugar in cidade.lugares for a in lugar.apelidos), key=lambda t: -len(t[0])
        )
    return _apelidos[cidade.id]


def no_dicionario(*textos: str, cidade: str = CIDADE_PADRAO) -> Lugar | None:
    """Primeiro lugar conhecido da cidade citado nos textos (o apelido mais específico vence)."""
    apelidos = _apelidos_da(obter(cidade))
    for texto in textos:
        alvo = normalizar(texto or "")
        if not alvo:
            continue
        for apelido, lugar in apelidos:
            if re.search(rf"\b{re.escape(apelido)}\b", alvo):
                return lugar
    return None


_trava = asyncio.Lock()
_ultima_chamada = 0.0


async def _nominatim(consulta: str, cidade: Cidade) -> tuple[float, float, str] | None:
    global _ultima_chamada
    if not settings.nominatim_enabled or not consulta.strip():
        return None
    params = {
        "q": f"{consulta}, {cidade.nome}, {cidade.uf}",
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "br",
        "viewbox": cidade.viewbox,
        "bounded": 1,
        "accept-language": "pt-BR",
    }
    async with _trava:
        # Política do Nominatim: no máximo 1 requisição por segundo.
        espera = 1.0 - (time.monotonic() - _ultima_chamada)
        if espera > 0:
            await asyncio.sleep(espera)
        try:
            async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": settings.http_user_agent}) as c:
                r = await c.get(settings.nominatim_url, params=params)
                r.raise_for_status()
                dados = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Nominatim indisponível para '{}': {}", consulta, exc)
            return None
        finally:
            _ultima_chamada = time.monotonic()
    if not dados:
        return None
    primeiro = dados[0]
    return float(primeiro["lat"]), float(primeiro["lon"]), str(primeiro.get("name") or consulta)


async def geocodificar(
    local: str, bairro: str = "", texto_completo: str = "", cidade: str = CIDADE_PADRAO
) -> Coordenada:
    c = obter(cidade)
    lugar = no_dicionario(local, bairro, texto_completo, cidade=c.id)
    if lugar:
        return Coordenada("dicionario", local or lugar.nome, lugar.lat, lugar.lng, lugar.nome, lugar.bairro)

    # Só o local primeiro: um bairro inferido errado zera a busca. No máximo 2 chamadas (1 req/s).
    tentativas = list(dict.fromkeys(t for t in (local, ", ".join(p for p in (local, bairro) if p), bairro) if t))
    for consulta in tentativas[:2]:
        achado = await _nominatim(consulta, c)
        if achado:
            lat, lng, nome = achado
            return Coordenada("nominatim", consulta, lat, lng, local or nome, bairro)

    return Coordenada(
        "centro", local or bairro or c.nome, c.lat, c.lng,
        local or f"Local não identificado ({c.nome})", bairro,
    )
