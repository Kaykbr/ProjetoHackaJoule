from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.ong import Ponto


class Demanda(Base):
    """Uma necessidade concreta publicada por uma ONG num ponto."""

    __tablename__ = "demandas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ponto_id: Mapped[int] = mapped_column(ForeignKey("pontos.id"), index=True)
    categoria: Mapped[str] = mapped_column(String(32), index=True)
    item: Mapped[str] = mapped_column(String(120))
    quantidade: Mapped[int] = mapped_column(Integer)
    #: Soma do que já foi prometido por doadores (ainda não entregue).
    quantidade_prometida: Mapped[int] = mapped_column(Integer, default=0)
    quantidade_recebida: Mapped[int] = mapped_column(Integer, default=0)
    #: 1 = baixa, 2 = média, 3 = alta — definida pela ONG (sugerida pela IA).
    urgencia_base: Mapped[int] = mapped_column(Integer, default=2)
    prazo: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="aberta", index=True)
    #: "ia" quando veio do extrator (e foi confirmada pela ONG) ou "manual".
    origem: Mapped[str] = mapped_column(String(16), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ponto: Mapped[Ponto] = relationship()

    @property
    def faltam(self) -> int:
        return max(0, self.quantidade - self.quantidade_recebida - self.quantidade_prometida)
