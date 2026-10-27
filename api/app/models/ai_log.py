from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AiLog(Base):
    """Uma chamada (ou tentativa) de IA. Alimenta o medidor de uso consciente."""

    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    feature: Mapped[str] = mapped_column(String(40), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(80))
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0)
    tokens_saida: Mapped[int] = mapped_column(Integer, default=0)
    latencia_ms: Mapped[int] = mapped_column(Integer, default=0)
    custo_estimado_usd: Mapped[float] = mapped_column(Float, default=0.0)
    #: True quando a resposta não veio da IA remota (regras, cache ou fallback).
    offline: Mapped[bool] = mapped_column(Boolean, default=False)
    #: "llm" | "regras" (cascata decidiu) | "cache" | "fallback" (IA falhou ou sem chave).
    origem: Mapped[str] = mapped_column(String(16), default="llm")
    #: Quantos dados pessoais (telefone, CPF, e-mail) foram removidos antes do envio.
    pii_removidos: Mapped[int] = mapped_column(Integer, default=0)
    #: Itens devolvidos sem evidência no texto e descartados.
    descartados: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
