"""Estado da central de operações: conversões, KPIs e utilidades compartilhadas."""
from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cidades import CIDADE_PADRAO
from app.config import settings
from app.models import BaseOperacional, Doador, PontoDemanda, RotaOtimizada
from app.schemas.ops import (
    BaseOut,
    DoadorOut,
    EstadoOut,
    ItemOps,
    KpisOut,
    PontoDemandaOut,
)
from app.services.geocoding import normalizar

#: Peso médio por unidade (kg), para estimar o desperdício evitado.
KG_POR_ITEM: dict[str, float] = {"alimentacao": 0.6, "agasalho": 1.2, "higiene": 0.4, "saude": 0.2}

#: Itens que podem substituir o pedido. Fora disso, não troca: água não vira marmita.
_GRUPOS_SUBSTITUTOS: tuple[set[str], ...] = (
    {"cobertor", "manta", "coberta", "edredom"},
    {"casaco", "blusa de frio", "moletom", "jaqueta", "agasalho"},
    {"marmita", "quentinha", "refeição"},
    {"garrafa de água", "água"},
    {"kit de curativo", "kit de primeiros socorros"},
    {"kit de higiene", "kit de higiene feminina"},
    {"lona", "capa de chuva"},
)


#: Mesmos grupos, comparados sem acento e sem caixa: o LLM às vezes devolve "agua".
_GRUPOS_NORMALIZADOS = tuple(frozenset(normalizar(n) for n in g) for g in _GRUPOS_SUBSTITUTOS)


def mesmo_item(a: str, b: str) -> bool:
    return normalizar(a) == normalizar(b)


def substitui(pedido: str, oferta: str) -> bool:
    p, o = normalizar(pedido), normalizar(oferta)
    return p == o or any(p in g and o in g for g in _GRUPOS_NORMALIZADOS)


def match_estoque(demandas: list[dict], estoques: list[dict]) -> tuple[int, int]:
    """(unidades pedidas que o estoque cobre, total pedido), com a mesma regra de substitutos."""
    disponivel: dict[str, int] = defaultdict(int)
    for e in estoques:
        disponivel[e["item"]] += int(e["quantidade"])
    coberto = total = 0
    # Itens exatos primeiro, para um substituto não "roubar" o estoque de quem pediu o original.
    for passo in ("exato", "substituto"):
        for d in demandas:
            falta = int(d["quantidade"]) - d.get("_coberto", 0)
            if passo == "exato":
                total += int(d["quantidade"])
            for item in list(disponivel):
                if falta <= 0:
                    break
                exato = mesmo_item(item, d["item"])
                serve = exato if passo == "exato" else (not exato and substitui(d["item"], item))
                if serve and disponivel[item] > 0:
                    q = min(falta, disponivel[item])
                    disponivel[item] -= q
                    falta -= q
                    d["_coberto"] = d.get("_coberto", 0) + q
                    coberto += q
    return coberto, total


def itens_validos(brutos: list[dict] | None) -> list[ItemOps]:
    saida: list[ItemOps] = []
    for b in brutos or []:
        try:
            saida.append(ItemOps.model_validate(b))
        except ValueError:
            continue
    return saida


def somar_itens(*listas: list[dict]) -> list[dict]:
    """Junta listas de itens somando quantidades do mesmo (categoria, item)."""
    total: dict[tuple[str, str], int] = defaultdict(int)
    for lista in listas:
        for i in lista:
            total[(i["categoria"], i["item"].strip().lower())] += int(i["quantidade"])
    return [{"categoria": c, "item": n, "quantidade": q} for (c, n), q in total.items() if q > 0]


def por_categoria(itens: list[dict] | list[ItemOps]) -> dict[str, int]:
    total: dict[str, int] = defaultdict(int)
    for i in itens:
        d = i.model_dump() if isinstance(i, ItemOps) else i
        total[d["categoria"]] += int(d["quantidade"])
    return dict(total)


def ponto_out(p: PontoDemanda) -> PontoDemandaOut:
    itens = itens_validos(p.itens)
    return PontoDemandaOut(
        id=p.id, nome=p.nome, bairro=p.bairro, lat=p.lat, lng=p.lng, pessoas=p.pessoas,
        urgencia=p.urgencia, resumo=p.resumo, itens=itens, condicoes=list(p.condicoes or []),
        origem=p.origem, relatos_30d=p.relatos_30d, status=p.status, transcricao=p.transcricao,
        atualizado_em=p.atualizado_em, total_itens=sum(i.quantidade for i in itens),
    )


def doador_out(d: Doador) -> DoadorOut:
    estoque = itens_validos(d.estoque)
    return DoadorOut(
        id=d.id, nome=d.nome, tipo=d.tipo, endereco=d.endereco, lat=d.lat, lng=d.lng,
        estoque=estoque, total_itens=sum(i.quantidade for i in estoque),
    )


def base(db: Session, cidade: str = CIDADE_PADRAO) -> BaseOperacional:
    b = db.scalars(
        select(BaseOperacional).where(BaseOperacional.cidade_id == cidade).order_by(BaseOperacional.id)
    ).first()
    if b is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Central sem dados. Rode o seed ou o reset.")
    return b


def pontos_abertos(db: Session, cidade: str = CIDADE_PADRAO) -> list[PontoDemanda]:
    return list(
        db.scalars(
            select(PontoDemanda)
            .where(PontoDemanda.status == "aberto", PontoDemanda.cidade_id == cidade)
            .order_by(PontoDemanda.id)
        )
    )


def doadores(db: Session, cidade: str = CIDADE_PADRAO) -> list[Doador]:
    return list(db.scalars(select(Doador).where(Doador.cidade_id == cidade).order_by(Doador.id)))


def kpis(db: Session, cidade: str = CIDADE_PADRAO) -> KpisOut:
    abertos = pontos_abertos(db, cidade)
    casado, total = match_estoque(
        [dict(i) for p in abertos for i in (p.itens or [])],
        [i for d in doadores(db, cidade) for i in (d.estoque or [])],
    )

    r = RotaOtimizada
    pessoas, kg, co2, rotas = db.execute(
        select(
            func.coalesce(func.sum(r.pessoas_atendidas), 0),
            func.coalesce(func.sum(r.kg_entregues), 0),
            func.coalesce(func.sum(r.co2_evitado_kg), 0),
            func.count(r.id),
        ).where(r.status == "concluida", r.cidade_id == cidade)
    ).one()
    return KpisOut(
        pessoas_assistidas=int(pessoas),
        match_doacoes_pct=round(100 * casado / total) if total else 100,
        kg_desperdicio_evitado=round(float(kg), 1),
        co2_economizado_kg=round(float(co2), 2),
        demandas_abertas=len(abertos),
        rotas_concluidas=int(rotas),
    )


def estado(db: Session, cidade: str = CIDADE_PADRAO) -> EstadoOut:
    return EstadoOut(
        base=BaseOut.model_validate(base(db, cidade)),
        demandas=[ponto_out(p) for p in pontos_abertos(db, cidade)],
        doadores=[doador_out(d) for d in doadores(db, cidade)],
        kpis=kpis(db, cidade),
        llm_ativo=settings.llm_enabled,
    )
