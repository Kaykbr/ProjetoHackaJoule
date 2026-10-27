"""Radar preditivo: previsão das próximas 24h × histórico dos pontos → risco futuro.

Tudo aqui é determinístico e explicável (sem LLM): cada ponto de risco vira uma frase em
`fatores`, e os alertas são montados com os mesmos números que o mapa mostra.

Fórmulas (0 a 1):
  frio  = (16 °C − mínima) / 11            → 0 a 16 °C, 1 a 5 °C
  calor = (máxima − 32 °C) / 6             → 0 a 32 °C, 1 a 38 °C
  chuva = probabilidade × (0,35 + mm/25)
  vento = (rajada − 15 km/h) / 45
  índice climático = 0,5·frio + 0,45·calor + 0,4·chuva + 0,1·vento (limitado a 1)
  vulnerabilidade  = 0,5·urgência/5 + 0,25·pessoas/30 + 0,25·relatos/12 (+0,1 com crianças, idosos…)
  risco = 100 · [1 − (1 − 0,85·vulnerabilidade) · (1 − 0,6·índice)]
"""
from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any

import httpx
from loguru import logger

from app.cidades import CIDADE_PADRAO, Cidade, obter
from app.config import settings
from app.models import PontoDemanda
from app.schemas.ops import (
    AlertaOut,
    Cenario,
    HoraPrevisao,
    ItemOps,
    PrevisaoOut,
    RadarOut,
    RiscoPontoOut,
)

_VULNERAVEIS = {"criancas", "idosos", "feridos", "gestantes", "doentes"}
#: Por cidade: (expira_em, série 24h, temperatura agora, chuva em mm); 15 min de validade.
_cache: dict[str, tuple[float, list[HoraPrevisao], float, float]] = {}


def _limitar(x: float) -> float:
    return max(0.0, min(1.0, x))


# ------------------------------------------------------------------ previsão


def _serie_padrao(cidade: Cidade) -> tuple[list[HoraPrevisao], float]:
    """Sem rede: um dia típico da cidade (ex.: 17–25 °C em SP), para a demo não depender da API."""
    minima, maxima = cidade.temp_padrao
    media, amplitude = (minima + maxima) / 2, (maxima - minima) / 2
    agora = datetime.now().replace(minute=0, second=0, microsecond=0)
    serie = []
    for h in range(24):
        hora = (agora.hour + h) % 24
        temp = media + amplitude * math.sin((hora - 9) / 24 * 2 * math.pi)
        serie.append(HoraPrevisao(hora=f"{hora:02d}:00", temp=round(temp, 1), chuva_prob=10, vento_kmh=9.0))
    return serie, serie[0].temp


async def _open_meteo(cidade: Cidade) -> tuple[list[HoraPrevisao], float, float] | None:
    """(série 24h, temperatura agora, chuva em mm nas 24h) ou None."""
    params = {
        "latitude": cidade.lat,
        "longitude": cidade.lng,
        "hourly": "temperature_2m,precipitation_probability,precipitation,wind_speed_10m",
        "current": "temperature_2m",
        "forecast_days": 2,
        "timezone": "America/Sao_Paulo",
    }
    try:
        async with httpx.AsyncClient(timeout=6.0) as c:
            r = await c.get(settings.clima_api_url, params=params)
            r.raise_for_status()
            dados = r.json()
        h = dados["hourly"]
        agora = dados["current"]["time"][:13]  # "2026-10-23T14"
        inicio = next((i for i, t in enumerate(h["time"]) if t[:13] >= agora), 0)
        fim = inicio + 24
        serie = [
            HoraPrevisao(
                hora=h["time"][i][11:16],
                temp=float(h["temperature_2m"][i]),
                chuva_prob=int(h["precipitation_probability"][i] or 0),
                vento_kmh=float(h["wind_speed_10m"][i] or 0),
            )
            for i in range(inicio, min(fim, len(h["time"])))
        ]
        mm = float(sum((h["precipitation"][i] or 0) for i in range(inicio, min(fim, len(h["time"])))))
        return serie, float(dados["current"]["temperature_2m"]), mm
    except (httpx.HTTPError, KeyError, TypeError, ValueError, StopIteration) as exc:
        logger.warning("Open-Meteo indisponível para {}: {}", cidade.nome, exc)
        return None


def _simular(serie: list[HoraPrevisao], cenario: Cenario) -> tuple[list[HoraPrevisao], float]:
    """Aplica o cenário de demo sobre a previsão real (mantém o formato do dia)."""
    if cenario == "frente_fria":
        queda = min(h.temp for h in serie) - 5.0  # leva a mínima para 5 °C
        nova = [h.model_copy(update={"temp": round(h.temp - max(queda, 6.0), 1),
                                     "vento_kmh": round(h.vento_kmh + 25, 1)}) for h in serie]
        return nova, 2.0
    if cenario == "tempestade":
        nova = [
            h.model_copy(update={
                "temp": round(h.temp - 3, 1),
                "chuva_prob": 95 if 4 <= i <= 18 else max(h.chuva_prob, 60),
                "vento_kmh": round(h.vento_kmh + (45 if 4 <= i <= 18 else 20), 1),
            })
            for i, h in enumerate(serie)
        ]
        return nova, 42.0
    if cenario == "onda_de_calor":
        alta = 38.0 - max(h.temp for h in serie)  # leva a máxima para 38 °C
        nova = [h.model_copy(update={"temp": round(h.temp + max(alta, 4.0), 1),
                                     "chuva_prob": min(h.chuva_prob, 5)}) for h in serie]
        return nova, 0.0
    return serie, 0.0


async def obter_previsao(cenario: Cenario = "normal", cidade: str = CIDADE_PADRAO) -> PrevisaoOut:
    c = obter(cidade)
    guardado = _cache.get(c.id)
    if guardado and time.monotonic() < guardado[0]:
        _, serie, temp_agora, mm = guardado
        fonte = "open-meteo"
    else:
        real = await _open_meteo(c) if settings.clima_enabled else None
        if real:
            serie, temp_agora, mm = real
            fonte = "open-meteo"
            _cache[c.id] = (time.monotonic() + 15 * 60, serie, temp_agora, mm)
        else:
            serie, temp_agora = _serie_padrao(c)
            mm, fonte = 0.0, "padrao"

    if cenario != "normal":
        serie, mm_extra = _simular(serie, cenario)
        mm = mm + mm_extra
        temp_agora = serie[0].temp
        fonte = "simulacao"

    return PrevisaoOut(
        fonte=fonte,  # type: ignore[arg-type]
        cenario=cenario,
        temp_agora=round(temp_agora, 1),
        temp_min_24h=round(min(h.temp for h in serie), 1),
        temp_max_24h=round(max(h.temp for h in serie), 1),
        chuva_prob_max=max(h.chuva_prob for h in serie),
        chuva_mm_24h=round(mm, 1),
        vento_max_kmh=round(max(h.vento_kmh for h in serie), 1),
        serie=serie,
    )



# ------------------------------------------------------------------ risco


def fatores_clima(p: PrevisaoOut) -> dict[str, float]:
    frio = _limitar((16 - p.temp_min_24h) / 11)
    calor = _limitar((p.temp_max_24h - 32) / 6)
    chuva = _limitar(p.chuva_prob_max / 100) * _limitar(0.35 + p.chuva_mm_24h / 25)
    vento = _limitar((p.vento_max_kmh - 15) / 45)
    indice = _limitar(0.5 * frio + 0.45 * calor + 0.4 * chuva + 0.1 * vento)
    return {"frio": frio, "calor": calor, "chuva": chuva, "vento": vento, "indice": indice}


def _fatores_agora(p: PrevisaoOut) -> dict[str, float]:
    """Mesmo cálculo, olhando só as próximas 3 horas (a 'visão atual')."""
    proximas = p.serie[:3] or p.serie
    agora = p.model_copy(update={
        "temp_min_24h": min(h.temp for h in proximas),
        "temp_max_24h": max(h.temp for h in proximas),
        "chuva_prob_max": max(h.chuva_prob for h in proximas),
        "chuva_mm_24h": p.chuva_mm_24h * len(proximas) / max(1, len(p.serie)),
        "vento_max_kmh": max(h.vento_kmh for h in proximas),
    })
    return fatores_clima(agora)


def vulnerabilidade(ponto: PontoDemanda) -> float:
    v = 0.5 * ponto.urgencia / 5 + 0.25 * min(1, ponto.pessoas / 30) + 0.25 * min(1, ponto.relatos_30d / 12)
    if _VULNERAVEIS & set(ponto.condicoes or []):
        v += 0.1
    return _limitar(v)


def risco(vuln: float, indice: float) -> int:
    """Combina vulnerabilidade e clima como riscos independentes: não satura em 100.

    Ex.: vulnerabilidade 0,9 → 76 sem clima adverso, 90 numa frente fria forte.
    """
    return round(100 * (1 - (1 - 0.85 * vuln) * (1 - 0.6 * indice)))


def nivel(score: int) -> str:
    if score >= 75:
        return "critico"
    if score >= 55:
        return "alto"
    if score >= 35:
        return "moderado"
    return "baixo"


def aumento_projetado(f: dict[str, float]) -> dict[str, int]:
    """% de aumento esperado na necessidade de cada categoria nas próximas 24h."""
    return {
        "agasalho": round(100 * (0.65 * f["frio"] + 0.45 * f["chuva"] + 0.15 * f["vento"])),
        # Água fica em alimentação: o calor pesa aqui.
        "alimentacao": round(100 * (0.15 * f["frio"] + 0.2 * f["chuva"] + 0.45 * f["calor"])),
        "higiene": round(100 * (0.25 * f["chuva"] + 0.15 * f["calor"])),
        "saude": round(100 * (0.3 * f["frio"] + 0.25 * f["chuva"] + 0.1 * f["vento"] + 0.35 * f["calor"])),
    }


def demanda_projetada(ponto: PontoDemanda, aumento: dict[str, int], f: dict[str, float]) -> list[ItemOps]:
    itens: list[dict[str, Any]] = [
        {**i, "quantidade": math.ceil(int(i["quantidade"]) * (1 + aumento.get(i["categoria"], 0) / 100))}
        for i in ponto.itens or []
    ]
    nomes = {i["item"] for i in itens}
    pessoas = max(ponto.pessoas, 1)
    # Necessidades que surgem com o clima mesmo sem ninguém ter pedido ainda.
    if f["frio"] >= 0.5 and not ({"cobertor", "manta", "coberta"} & nomes):
        itens.append({"categoria": "agasalho", "item": "cobertor", "quantidade": pessoas})
    if f["chuva"] >= 0.5 and "lona" not in nomes:
        itens.append({"categoria": "agasalho", "item": "lona", "quantidade": math.ceil(pessoas / 3)})
    if f["calor"] >= 0.5 and not ({"garrafa de água", "água", "agua"} & nomes):
        itens.append({"categoria": "alimentacao", "item": "garrafa de água", "quantidade": pessoas * 2})
    return [ItemOps.model_validate(i) for i in itens if i["quantidade"] > 0]


def _fatores_texto(ponto: PontoDemanda, p: PrevisaoOut, f: dict[str, float]) -> list[str]:
    fatores = [f"Urgência {ponto.urgencia}/5 relatada"]
    if ponto.pessoas:
        fatores.append(f"{ponto.pessoas} pessoas no local")
    if ponto.relatos_30d >= 6:
        fatores.append(f"{ponto.relatos_30d} relatos nos últimos 30 dias")
    if vulneraveis := _VULNERAVEIS & set(ponto.condicoes or []):
        nomes = {"criancas": "crianças", "idosos": "idosos", "feridos": "feridos", "gestantes": "gestantes", "doentes": "doentes"}
        fatores.append("Há " + ", ".join(nomes[v] for v in sorted(vulneraveis)) + " no local")
    if f["frio"] >= 0.3:
        fatores.append(f"Mínima de {p.temp_min_24h:.0f}°C nas próximas 24h")
    if f["calor"] >= 0.3:
        fatores.append(f"Máxima de {p.temp_max_24h:.0f}°C nas próximas 24h")
    if f["chuva"] >= 0.3:
        fatores.append(f"Chuva provável ({p.chuva_prob_max}%, {p.chuva_mm_24h:.0f} mm)")
    if f["vento"] >= 0.4:
        fatores.append(f"Vento de até {p.vento_max_kmh:.0f} km/h")
    return fatores


def _alertas(p: PrevisaoOut, f: dict[str, float], aumento: dict[str, int], riscos: list[RiscoPontoOut],
             nomes: dict[int, str]) -> list[AlertaOut]:
    severidade = "critico" if f["indice"] >= 0.6 else "atencao"
    altos = [r.ponto_id for r in riscos if r.risco_24h >= 55]
    alertas: list[AlertaOut] = []
    if f["frio"] >= 0.5:
        alertas.append(AlertaOut(
            id="frio", severidade=severidade, categoria="agasalho", aumento_pct=aumento["agasalho"], pontos=altos,
            titulo=f"Frio intenso: mínima de {p.temp_min_24h:.0f}°C",
            descricao=f"Aumento projetado de +{aumento['agasalho']}% na necessidade de agasalhos e cobertores "
                      f"nas próximas 24h. {len(altos)} ponto(s) com risco alto ou crítico.",
        ))
    if f["calor"] >= 0.5:
        alertas.append(AlertaOut(
            id="calor", severidade=severidade, categoria="alimentacao", aumento_pct=aumento["alimentacao"], pontos=altos,
            titulo=f"Calor extremo: máxima de {p.temp_max_24h:.0f}°C",
            descricao=f"Aumento projetado de +{aumento['alimentacao']}% em água e alimento e +{aumento['saude']}% em "
                      "saúde (desidratação, insolação) nas próximas 24h. Leve água primeiro.",
        ))
    if f["chuva"] >= 0.5:
        alertas.append(AlertaOut(
            id="chuva", severidade=severidade, categoria="agasalho", aumento_pct=aumento["agasalho"], pontos=altos,
            titulo=f"Chuva forte prevista: {p.chuva_prob_max}% de chance, {p.chuva_mm_24h:.0f} mm",
            descricao=f"Projeção de +{aumento['agasalho']}% em lonas e capas e +{aumento['saude']}% em itens de "
                      "saúde. Priorize pontos sem cobertura.",
        ))
    if f["vento"] >= 0.5:
        alertas.append(AlertaOut(
            id="vento", severidade="atencao", titulo=f"Ventos de até {p.vento_max_kmh:.0f} km/h",
            descricao="Abrigos improvisados podem ceder. Lonas e cordas ajudam a fixar coberturas.", pontos=altos,
        ))
    for r in sorted(riscos, key=lambda r: -r.risco_24h)[:3]:
        if r.risco_24h >= 75:
            alertas.append(AlertaOut(
                id=f"ponto-{r.ponto_id}", severidade="critico", pontos=[r.ponto_id],
                titulo=f"{nomes[r.ponto_id]}: risco {r.risco_24h}/100 em 24h",
                descricao=". ".join(r.fatores[:3]) + ".",
            ))
    if not alertas:
        alertas.append(AlertaOut(
            id="estavel", severidade="info", titulo="Sem alerta climático nas próximas 24h",
            descricao="A prioridade segue a urgência relatada pelos voluntários.",
        ))
    return alertas


async def calcular_radar(
    pontos: list[PontoDemanda], cenario: Cenario = "normal", cidade: str = CIDADE_PADRAO
) -> RadarOut:
    previsao = await obter_previsao(cenario, cidade)
    f24 = fatores_clima(previsao)
    fagora = _fatores_agora(previsao)
    aumento = aumento_projetado(f24)

    riscos = []
    for ponto in pontos:
        vuln = vulnerabilidade(ponto)
        r24 = risco(vuln, f24["indice"])
        riscos.append(RiscoPontoOut(
            ponto_id=ponto.id,
            risco_atual=risco(vuln, fagora["indice"]),
            risco_24h=r24,
            nivel=nivel(r24),  # type: ignore[arg-type]
            fatores=_fatores_texto(ponto, previsao, f24),
            demanda_projetada=demanda_projetada(ponto, aumento, f24),
        ))

    return RadarOut(
        cenario=cenario,
        previsao=previsao,
        indice_clima=round(100 * f24["indice"]),
        riscos=riscos,
        alertas=_alertas(previsao, f24, aumento, riscos, {p.id: p.nome for p in pontos}),
        aumento_projetado=aumento,
    )
