from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.cidades import CIDADE_PADRAO, CidadeId
from app.database import get_db
from app.schemas import (
    DemandaOut,
    DemandasCreateIn,
    DemandaStatusIn,
    ExtracaoIn,
    ExtracaoOut,
)
from app.services import demandas, extracao

router = APIRouter(prefix="/demandas", tags=["demandas"])


@router.get("", response_model=list[DemandaOut])
def listar(
    status_: Literal["aberta", "atendida", "cancelada", "todas"] = Query("aberta", alias="status"),
    categoria: str | None = None,
    ong_id: int | None = None,
    cidade: CidadeId = Query(CIDADE_PADRAO),
    db: Session = Depends(get_db),
) -> list[DemandaOut]:
    filtro = None if status_ == "todas" else status_
    return demandas.listar(db, status_=filtro, categoria=categoria, ong_id=ong_id, cidade=cidade)


@router.post("/extrair", response_model=ExtracaoOut)
def extrair(dados: ExtracaoIn, db: Session = Depends(get_db)) -> ExtracaoOut:
    """Texto/áudio transcrito da ONG → proposta de itens. Nada é salvo aqui."""
    return extracao.extrair(db, dados.texto, "demanda")


@router.post("", response_model=list[DemandaOut], status_code=status.HTTP_201_CREATED)
def publicar(dados: DemandasCreateIn, db: Session = Depends(get_db)) -> list[DemandaOut]:
    """Publica os itens que a ONG revisou e confirmou."""
    return demandas.criar(db, dados)


@router.patch("/{demanda_id}", response_model=DemandaOut)
def alterar_status(
    demanda_id: int, dados: DemandaStatusIn, db: Session = Depends(get_db)
) -> DemandaOut:
    return demandas.alterar_status(db, demanda_id, dados.status)
