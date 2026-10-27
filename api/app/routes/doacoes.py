from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.cidades import CIDADE_PADRAO, CidadeId
from app.database import get_db
from app.schemas import (
    DoacaoIn,
    DoacaoOut,
    DoacaoStatusIn,
    ExtracaoIn,
    ExtracaoOut,
    SugestaoOut,
    SugestoesIn,
)
from app.services import demandas, extracao, matching

router = APIRouter(tags=["doações"])


@router.post("/ofertas/extrair", response_model=ExtracaoOut)
def extrair_oferta(dados: ExtracaoIn, db: Session = Depends(get_db)) -> ExtracaoOut:
    """'Tenho 3 casacos e uns sabonetes' → itens estruturados para o doador revisar."""
    return extracao.extrair(db, dados.texto, "oferta")


@router.post("/ofertas/sugestoes", response_model=list[SugestaoOut])
def sugerir(
    dados: SugestoesIn, cidade: CidadeId = Query(CIDADE_PADRAO), db: Session = Depends(get_db)
) -> list[SugestaoOut]:
    return matching.sugerir(db, dados.itens, dados.lat, dados.lng, cidade=cidade)


@router.get("/doacoes", response_model=list[DoacaoOut])
def listar(ong_id: int | None = None, db: Session = Depends(get_db)) -> list[DoacaoOut]:
    return demandas.listar_doacoes(db, ong_id=ong_id)


@router.post("/doacoes", response_model=DoacaoOut, status_code=status.HTTP_201_CREATED)
def prometer(dados: DoacaoIn, db: Session = Depends(get_db)) -> DoacaoOut:
    return demandas.prometer(db, dados)


@router.patch("/doacoes/{doacao_id}", response_model=DoacaoOut)
def alterar_status(
    doacao_id: int, dados: DoacaoStatusIn, db: Session = Depends(get_db)
) -> DoacaoOut:
    return demandas.alterar_status_doacao(db, doacao_id, dados.status)
