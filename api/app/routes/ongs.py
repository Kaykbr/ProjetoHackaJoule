from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.catalogo import CATEGORIAS
from app.cidades import CIDADE_PADRAO, CIDADES, CidadeId
from app.database import get_db
from app.models import Ong, Ponto
from app.schemas import CategoriaOut, CenarioOut, CidadeOut, OngOut, PontoIn, PontoOut, RelatoExemploOut
from app.services.demandas import ponto_out

router = APIRouter(tags=["ongs"])
CidadeQ = Query(CIDADE_PADRAO, description="sp, rj ou for")


@router.get("/cidades", response_model=list[CidadeOut])
def listar_cidades() -> list[CidadeOut]:
    """Cidades disponíveis, com cenários de clima plausíveis e relatos de exemplo."""
    return [
        CidadeOut(
            id=c.id, nome=c.nome, uf=c.uf, lat=c.lat, lng=c.lng,
            cenarios=[CenarioOut(id=i, rotulo=r) for i, r in c.cenarios],
            relatos_exemplo=[RelatoExemploOut(rotulo=r, texto=t) for r, t in c.relatos_exemplo],
        )
        for c in CIDADES.values()
    ]


@router.get("/categorias", response_model=list[CategoriaOut])
def listar_categorias() -> list[CategoriaOut]:
    return [
        CategoriaOut(
            slug=c.slug, nome=c.nome, sensivel_frio=c.sensivel_frio, sensivel_calor=c.sensivel_calor
        )
        for c in CATEGORIAS
    ]


@router.get("/ongs", response_model=list[OngOut])
def listar_ongs(cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> list[Ong]:
    return list(db.scalars(select(Ong).where(Ong.cidade_id == cidade).order_by(Ong.nome)).all())


@router.get("/pontos", response_model=list[PontoOut])
def listar_pontos(
    ong_id: int | None = None, cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)
) -> list[PontoOut]:
    query = (
        select(Ponto).join(Ong, Ponto.ong_id == Ong.id).where(Ong.cidade_id == cidade)
        .options(joinedload(Ponto.ong)).order_by(Ponto.regiao, Ponto.nome)
    )
    if ong_id:
        query = query.where(Ponto.ong_id == ong_id)
    return [ponto_out(p) for p in db.scalars(query).all()]


@router.post("/pontos", response_model=PontoOut, status_code=status.HTTP_201_CREATED)
def criar_ponto(dados: PontoIn, db: Session = Depends(get_db)) -> PontoOut:
    if db.get(Ong, dados.ong_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ONG não encontrada.")
    ponto = Ponto(**dados.model_dump())
    db.add(ponto)
    db.commit()
    db.refresh(ponto)
    return ponto_out(ponto)
