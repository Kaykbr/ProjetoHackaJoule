"""Doador → demanda: onde cada item faz mais diferença agora.

Score determinístico = urgência efetiva × peso + proximidade × peso (configuráveis).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.schemas import ItemOfertaIn, OpcaoOut, SugestaoOut
from app.services import demandas
from app.services.geo import distancia_km


def _proximidade(km: float) -> float:
    """0–100: 100 colado no doador, 0 na borda do raio de busca."""
    return max(0.0, 1 - km / settings.raio_busca_km) * 100


def sugerir(
    db: Session, itens: list[ItemOfertaIn], lat: float, lng: float, limite: int = 3,
    cidade: str | None = None,
) -> list[SugestaoOut]:
    abertas = [d for d in demandas.listar(db, cidade=cidade) if d.faltam > 0]
    sugestoes: list[SugestaoOut] = []

    for item in itens:
        opcoes: list[OpcaoOut] = []
        for d in abertas:
            if d.categoria != item.categoria:
                continue
            km = distancia_km(lat, lng, d.ponto.lat, d.ponto.lng)
            score = round(
                d.urgencia.score * settings.peso_urgencia
                + _proximidade(km) * settings.peso_proximidade
            )
            razoes = [f"a {km:.1f} km de você".replace(".", ","), *d.urgencia.razoes]
            if d.faltam <= item.quantidade:
                razoes.append(f"sua doação completa o pedido (faltam {d.faltam})")
            opcoes.append(
                OpcaoOut(
                    demanda=d,
                    distancia_km=round(km, 2),
                    score=score,
                    quantidade_sugerida=min(item.quantidade, d.faltam),
                    razoes=razoes,
                )
            )
        opcoes.sort(key=lambda o: o.score, reverse=True)
        sugestoes.append(SugestaoOut(item=item, opcoes=opcoes[:limite]))
    return sugestoes
