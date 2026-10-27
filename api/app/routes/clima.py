from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cidades import CIDADE_PADRAO, CidadeId
from app.config import settings
from app.database import get_db
from app.models import Ong, Ponto
from app.schemas import ClimaOut, ClimaRegiaoOut, ImpactoOut, SimulacaoIn
from app.services import clima, impacto

router = APIRouter(tags=["clima e impacto"])
CidadeQ = Query(CIDADE_PADRAO, description="sp, rj ou for")


def _estado(db: Session, cidade: str) -> ClimaOut:
    regioes: dict[str, ClimaRegiaoOut] = {}
    pontos = select(Ponto).join(Ong, Ponto.ong_id == Ong.id).where(Ong.cidade_id == cidade)
    for ponto in db.scalars(pontos.order_by(Ponto.regiao)).all():
        if ponto.regiao in regioes:
            continue
        p = clima.previsao(ponto.lat, ponto.lng, cidade)
        regioes[ponto.regiao] = ClimaRegiaoOut(
            regiao=ponto.regiao,
            temp_min=p.temp_min if p else None,
            temp_max=p.temp_max if p else None,
            fonte=p.fonte if p else "indisponivel",
        )

    alertas: list[str] = []
    frias = [r for r in regioes.values() if r.temp_min is not None and r.temp_min <= settings.frio_limite_c]
    quentes = [r for r in regioes.values() if r.temp_max is not None and r.temp_max >= settings.calor_limite_c]
    if frias:
        menor = min(r.temp_min for r in frias if r.temp_min is not None)
        alertas.append(
            f"Frio de até {menor:.0f}°C previsto: agasalhos e cobertores foram priorizados."
        )
    if quentes:
        maior = max(r.temp_max for r in quentes if r.temp_max is not None)
        alertas.append(f"Calor de até {maior:.0f}°C previsto: água foi priorizada.")
    return ClimaOut(simulacao=clima.simulacao_ativa(cidade), regioes=list(regioes.values()), alertas=alertas)


@router.get("/clima", response_model=ClimaOut)
def estado(cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> ClimaOut:
    return _estado(db, cidade)


@router.post("/clima/simulacao", response_model=ClimaOut)
def simular(dados: SimulacaoIn, cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> ClimaOut:
    """Modo demo: força uma previsão (frente fria em SP, calor no RJ/Fortaleza) na cidade."""
    clima.simular(dados.temp_min, dados.temp_max, cidade)
    return _estado(db, cidade)


@router.delete("/clima/simulacao", response_model=ClimaOut)
def parar_simulacao(cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> ClimaOut:
    clima.limpar_simulacao(cidade)
    return _estado(db, cidade)


@router.get("/impacto", response_model=ImpactoOut)
def resumo(cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> ImpactoOut:
    return impacto.resumo(db, cidade)
