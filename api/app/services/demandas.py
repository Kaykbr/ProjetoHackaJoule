"""Ciclo de vida de demandas e doações + montagem das respostas com urgência."""
from __future__ import annotations

from datetime import date

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.catalogo import POR_SLUG
from app.models import Demanda, Doacao, Ong, Ponto
from app.schemas import DemandaOut, DemandasCreateIn, DoacaoIn, DoacaoOut, PontoOut, UrgenciaOut
from app.services import clima, urgencia


def ponto_out(ponto: Ponto) -> PontoOut:
    return PontoOut(
        id=ponto.id,
        ong_id=ponto.ong_id,
        ong_nome=ponto.ong.nome,
        nome=ponto.nome,
        regiao=ponto.regiao,
        lat=ponto.lat,
        lng=ponto.lng,
        referencia=ponto.referencia,
        modo_recebimento=ponto.modo_recebimento,
    )


def demanda_out(demanda: Demanda, hoje: date | None = None) -> DemandaOut:
    previsao = clima.previsao(demanda.ponto.lat, demanda.ponto.lng, demanda.ponto.ong.cidade_id)
    u = urgencia.calcular(demanda, previsao, hoje)
    return DemandaOut(
        id=demanda.id,
        ponto=ponto_out(demanda.ponto),
        categoria=demanda.categoria,
        categoria_nome=POR_SLUG[demanda.categoria].nome if demanda.categoria in POR_SLUG else "Outros",
        item=demanda.item,
        quantidade=demanda.quantidade,
        quantidade_prometida=demanda.quantidade_prometida,
        quantidade_recebida=demanda.quantidade_recebida,
        faltam=demanda.faltam,
        urgencia_base=demanda.urgencia_base,
        prazo=demanda.prazo,
        status=demanda.status,
        origem=demanda.origem,
        urgencia=UrgenciaOut(score=u.score, nivel=u.nivel, razoes=u.razoes),
        created_at=demanda.created_at,
    )


def _query_demandas():
    return select(Demanda).options(joinedload(Demanda.ponto).joinedload(Ponto.ong))


def listar(
    db: Session,
    *,
    status_: str | None = "aberta",
    categoria: str | None = None,
    ong_id: int | None = None,
    cidade: str | None = None,
) -> list[DemandaOut]:
    query = _query_demandas()
    if cidade:
        pontos_da_cidade = select(Ponto.id).join(Ong, Ponto.ong_id == Ong.id).where(Ong.cidade_id == cidade)
        query = query.where(Demanda.ponto_id.in_(pontos_da_cidade))
    if status_:
        query = query.where(Demanda.status == status_)
    if categoria:
        query = query.where(Demanda.categoria == categoria)
    if ong_id:
        query = query.join(Demanda.ponto).where(Ponto.ong_id == ong_id)
    demandas = db.scalars(query).unique().all()
    saida = [demanda_out(d) for d in demandas]
    return sorted(saida, key=lambda d: d.urgencia.score, reverse=True)


def obter(db: Session, demanda_id: int) -> Demanda:
    demanda = db.scalars(_query_demandas().where(Demanda.id == demanda_id)).first()
    if demanda is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demanda não encontrada.")
    return demanda


def criar(db: Session, dados: DemandasCreateIn) -> list[DemandaOut]:
    ponto = db.get(Ponto, dados.ponto_id)
    if ponto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ponto não encontrado.")
    novas = [
        Demanda(
            ponto_id=ponto.id,
            categoria=item.categoria,
            item=item.item,
            quantidade=item.quantidade,
            urgencia_base=item.urgencia,
            prazo=item.prazo,
            origem=dados.origem,
        )
        for item in dados.itens
    ]
    db.add_all(novas)
    db.commit()
    logger.info("{} demanda(s) publicadas no ponto {} (origem={})", len(novas), ponto.id, dados.origem)
    return [demanda_out(obter(db, d.id)) for d in novas]


def alterar_status(db: Session, demanda_id: int, novo: str) -> DemandaOut:
    demanda = obter(db, demanda_id)
    demanda.status = novo
    db.commit()
    return demanda_out(demanda)


# ---------------------------------------------------------------- doações


def doacao_out(doacao: Doacao) -> DoacaoOut:
    return DoacaoOut(
        id=doacao.id,
        demanda=demanda_out(doacao.demanda),
        quantidade=doacao.quantidade,
        doador_apelido=doacao.doador_apelido,
        status=doacao.status,
        created_at=doacao.created_at,
    )


def prometer(db: Session, dados: DoacaoIn) -> DoacaoOut:
    demanda = obter(db, dados.demanda_id)
    if demanda.status != "aberta":
        raise HTTPException(status.HTTP_409_CONFLICT, "Essa demanda não está mais aberta.")
    if demanda.faltam <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Essa demanda já está toda coberta.")
    quantidade = min(dados.quantidade, demanda.faltam)
    doacao = Doacao(
        demanda_id=demanda.id,
        quantidade=quantidade,
        doador_apelido=dados.doador_apelido.strip() or "Anônimo",
    )
    demanda.quantidade_prometida += quantidade
    db.add(doacao)
    db.commit()
    db.refresh(doacao)
    return doacao_out(doacao)


def listar_doacoes(db: Session, *, ong_id: int | None = None) -> list[DoacaoOut]:
    query = (
        select(Doacao)
        .options(joinedload(Doacao.demanda).joinedload(Demanda.ponto).joinedload(Ponto.ong))
        .order_by(Doacao.created_at.desc(), Doacao.id.desc())
    )
    if ong_id:
        query = query.join(Doacao.demanda).join(Demanda.ponto).where(Ponto.ong_id == ong_id)
    return [doacao_out(d) for d in db.scalars(query).unique().all()]


def alterar_status_doacao(db: Session, doacao_id: int, novo: str) -> DoacaoOut:
    doacao = db.get(Doacao, doacao_id)
    if doacao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doação não encontrada.")
    if doacao.status != "prometida":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Doação já está {doacao.status}.")

    demanda = obter(db, doacao.demanda_id)
    demanda.quantidade_prometida = max(0, demanda.quantidade_prometida - doacao.quantidade)
    if novo == "entregue":
        demanda.quantidade_recebida += doacao.quantidade
        if demanda.quantidade_recebida >= demanda.quantidade:
            demanda.status = "atendida"
    doacao.status = novo
    db.commit()
    db.refresh(doacao)
    return doacao_out(doacao)
