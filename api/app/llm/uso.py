"""Registro de cada uso de IA (alimenta o medidor de uso consciente)."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.llm.client import Resultado
from app.models import AiLog


def estimar_tokens(texto: str) -> int:
    return max(1, len(texto) // 4)


def custo_usd(entrada: int, saida: int) -> float:
    return (
        entrada * settings.llm_preco_entrada_por_milhao
        + saida * settings.llm_preco_saida_por_milhao
    ) / 1_000_000


def pode_chamar_llm(db: Session) -> bool:
    """False quando o teto diário (LLM_MAX_CHAMADAS_DIA) foi atingido: protege a chave no site público."""
    hoje = datetime.combine(date.today(), datetime.min.time())
    feitas = db.scalar(
        select(func.count(AiLog.id)).where(AiLog.origem == "llm", AiLog.created_at >= hoje)
    ) or 0
    return feitas < settings.llm_max_chamadas_dia


def origem_de(resultado: Resultado) -> str:
    return "fallback" if resultado.offline else "llm"


def registrar_uso(
    db: Session,
    feature: str,
    resultado: Resultado | None,
    prompt: str,
    latencia_ms: int,
    pii: int,
    *,
    origem: str | None = None,
    descartados: int = 0,
) -> None:
    """Uma linha por mensagem processada. Sem `resultado` (cache/regras), não houve chamada."""
    entrada = saida = 0
    if resultado is not None and not resultado.offline:
        c = resultado.completion
        entrada = c.tokens_entrada or estimar_tokens(prompt)
        saida = c.tokens_saida or estimar_tokens(c.texto)
    origem = origem or (origem_de(resultado) if resultado else "regras")
    db.add(
        AiLog(
            feature=feature,
            provider=resultado.provider if resultado else origem,
            model=resultado.model if resultado else "-",
            tokens_entrada=entrada,
            tokens_saida=saida,
            latencia_ms=latencia_ms,
            custo_estimado_usd=custo_usd(entrada, saida),
            offline=origem != "llm",
            origem=origem,
            pii_removidos=pii,
            descartados=descartados,
        )
    )
    db.commit()
