"""Números do painel de impacto e do medidor de uso de IA."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cidades import CIDADE_PADRAO
from app.config import settings
from app.models import AiLog, Demanda, Doacao, Ong, Ponto
from app.schemas import ImpactoOut, UsoIaOut


def _contar(db: Session, query) -> int:
    return int(db.scalar(query) or 0)


def resumo(db: Session, cidade: str = CIDADE_PADRAO) -> ImpactoOut:
    """Números da cidade. O medidor de IA é do sistema todo (a chave e o custo são um só)."""
    da_cidade = Ong.cidade_id == cidade
    pontos = select(Ponto.id).join(Ong, Ponto.ong_id == Ong.id).where(da_cidade)
    demandas = select(Demanda.id).where(Demanda.ponto_id.in_(pontos))
    doacoes = select(Doacao.quantidade).where(Doacao.demanda_id.in_(demandas))
    por_origem = dict(db.execute(select(AiLog.origem, func.count(AiLog.id)).group_by(AiLog.origem)).all())
    chamadas = sum(por_origem.values())
    remotas = por_origem.get("llm", 0)
    custo = float(db.scalar(select(func.coalesce(func.sum(AiLog.custo_estimado_usd), 0))) or 0)

    return ImpactoOut(
        ongs=_contar(db, select(func.count(Ong.id)).where(da_cidade)),
        pontos=_contar(db, select(func.count()).select_from(pontos.subquery())),
        demandas_abertas=_contar(
            db, select(func.count(Demanda.id)).where(Demanda.id.in_(demandas), Demanda.status == "aberta")
        ),
        demandas_atendidas=_contar(
            db, select(func.count(Demanda.id)).where(Demanda.id.in_(demandas), Demanda.status == "atendida")
        ),
        itens_prometidos=_contar(
            db, select(func.sum(Doacao.quantidade)).where(Doacao.demanda_id.in_(demandas), Doacao.status == "prometida")
        ),
        itens_entregues=_contar(
            db, select(func.sum(Doacao.quantidade)).where(Doacao.demanda_id.in_(demandas), Doacao.status == "entregue")
        ),
        doacoes=_contar(db, select(func.count()).select_from(doacoes.subquery())),
        ia=UsoIaOut(
            llm_ativo=settings.llm_enabled,
            provider=settings.provider_efetivo,
            modelo=settings.modelo_efetivo,
            chamadas=chamadas,
            chamadas_offline=chamadas - remotas,
            chamadas_llm=remotas,
            resolvidas_regras=por_origem.get("regras", 0),
            cache_hits=por_origem.get("cache", 0),
            fallback=por_origem.get("fallback", 0),
            itens_sem_evidencia=_contar(db, select(func.sum(AiLog.descartados))),
            tokens=_contar(db, select(func.sum(AiLog.tokens_entrada + AiLog.tokens_saida))),
            custo_estimado_usd=round(custo, 6),
            custo_medio_usd=round(custo / remotas, 8) if remotas else 0.0,
            pii_removidos=_contar(db, select(func.sum(AiLog.pii_removidos))),
        ),
    )
