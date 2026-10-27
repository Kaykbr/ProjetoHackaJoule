"""Previsão do tempo via Open-Meteo (gratuito, sem chave) com cache e modo simulação.

A simulação existe para a demo: "chegou uma frente fria" muda as urgências ao vivo,
sem depender do tempo real no dia da apresentação.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from loguru import logger

from app.config import settings


@dataclass(frozen=True)
class Previsao:
    temp_min: float
    temp_max: float
    fonte: str  # "open-meteo" | "simulacao"


_cache: dict[tuple[float, float], tuple[float, Previsao | None]] = {}
#: Simulação da demo, por cidade (calor no Rio não vaza para São Paulo).
_simulacoes: dict[str, Previsao] = {}

#: Depois de uma falha de rede, espera este tempo antes de tentar de novo.
_ESPERA_APOS_FALHA_S = 300


def simular(temp_min: float, temp_max: float, cidade: str = "sp") -> Previsao:
    _simulacoes[cidade] = Previsao(temp_min=temp_min, temp_max=temp_max, fonte="simulacao")
    logger.info("Simulação de clima ativada em {}: min={} max={}", cidade, temp_min, temp_max)
    return _simulacoes[cidade]


def limpar_simulacao(cidade: str | None = None) -> None:
    """Desliga a simulação de uma cidade (ou de todas, sem argumento)."""
    if cidade is None:
        _simulacoes.clear()
    else:
        _simulacoes.pop(cidade, None)
    logger.info("Simulação de clima desativada ({}).", cidade or "todas")


def simulacao_ativa(cidade: str = "sp") -> bool:
    return cidade in _simulacoes


def previsao(lat: float, lng: float, cidade: str = "sp") -> Previsao | None:
    """Mínima e máxima dos próximos dias para a região. `None` se indisponível."""
    if (simulada := _simulacoes.get(cidade)) is not None:
        return simulada
    if not settings.clima_enabled:
        return None

    # ~11 km de resolução: pontos do mesmo bairro compartilham a mesma consulta.
    chave = (round(lat, 1), round(lng, 1))
    agora = time.monotonic()
    em_cache = _cache.get(chave)
    if em_cache is not None:
        expira_em, valor = em_cache
        if agora < expira_em:
            return valor

    valor = _buscar(*chave)
    ttl = settings.clima_cache_minutos * 60 if valor else _ESPERA_APOS_FALHA_S
    _cache[chave] = (agora + ttl, valor)
    return valor


def _buscar(lat: float, lng: float) -> Previsao | None:
    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": "temperature_2m_min,temperature_2m_max",
        "forecast_days": settings.clima_dias_previsao,
        "timezone": "America/Sao_Paulo",
    }
    try:
        response = httpx.get(settings.clima_api_url, params=params, timeout=4.0)
        response.raise_for_status()
        daily = response.json()["daily"]
        return Previsao(
            temp_min=float(min(daily["temperature_2m_min"])),
            temp_max=float(max(daily["temperature_2m_max"])),
            fonte="open-meteo",
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        logger.warning("Clima indisponível para ({}, {}): {}", lat, lng, exc)
        return None
