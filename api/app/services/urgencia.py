"""Urgência efetiva de uma demanda — regras determinísticas e explicáveis.

Nada aqui usa LLM: o score é reproduzível e cada ponto somado vira uma razão
legível na interface ("frio de 8°C previsto", "prazo amanhã").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.catalogo import POR_SLUG
from app.config import settings
from app.models import Demanda
from app.services.clima import Previsao

_BASE = {1: 20, 2: 40, 3: 60}
_ROTULO_BASE = {
    1: "prioridade baixa para a ONG",
    2: "prioridade média para a ONG",
    3: "prioridade alta para a ONG",
}


@dataclass
class Urgencia:
    score: int
    nivel: str
    razoes: list[str] = field(default_factory=list)


def nivel_do_score(score: int) -> str:
    if score >= 75:
        return "critica"
    if score >= 50:
        return "alta"
    if score >= 30:
        return "media"
    return "baixa"


def calcular(demanda: Demanda, previsao: Previsao | None, hoje: date | None = None) -> Urgencia:
    hoje = hoje or date.today()
    base = demanda.urgencia_base if demanda.urgencia_base in _BASE else 2
    score = _BASE[base]
    razoes = [_ROTULO_BASE[base]]

    if demanda.prazo is not None:
        dias = (demanda.prazo - hoje).days
        if dias <= 1:
            score += 20
            razoes.append("prazo hoje ou amanhã" if dias >= 0 else "prazo vencido")
        elif dias <= 3:
            score += 10
            razoes.append(f"prazo em {dias} dias")

    if demanda.quantidade > 0:
        cobertura = (demanda.quantidade_recebida + demanda.quantidade_prometida) / demanda.quantidade
        if cobertura < 0.25:
            score += 10
            razoes.append(f"só {cobertura:.0%} do pedido atendido")
        elif cobertura >= 0.75:
            score -= 15
            razoes.append(f"{cobertura:.0%} do pedido já atendido")

    categoria = POR_SLUG.get(demanda.categoria)
    if previsao is not None and categoria is not None:
        sufixo = " (simulação)" if previsao.fonte == "simulacao" else ""
        if categoria.sensivel_frio and previsao.temp_min <= settings.frio_extremo_c:
            score += 25
            razoes.append(f"frio extremo previsto: {previsao.temp_min:.0f}°C{sufixo}")
        elif categoria.sensivel_frio and previsao.temp_min <= settings.frio_limite_c:
            score += 15
            razoes.append(f"frio previsto: {previsao.temp_min:.0f}°C{sufixo}")
        if categoria.sensivel_calor and previsao.temp_max >= settings.calor_limite_c:
            score += 20
            razoes.append(f"calor previsto: {previsao.temp_max:.0f}°C{sufixo}")

    score = max(0, min(100, score))
    return Urgencia(score=score, nivel=nivel_do_score(score), razoes=razoes)
