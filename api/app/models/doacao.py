from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.demanda import Demanda


class Doacao(Base):
    """Compromisso de um doador com uma demanda: prometida → entregue (ou cancelada)."""

    __tablename__ = "doacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    demanda_id: Mapped[int] = mapped_column(ForeignKey("demandas.id"), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    #: Só um apelido: o MVP não coleta dados pessoais do doador.
    doador_apelido: Mapped[str] = mapped_column(String(60), default="Anônimo")
    status: Mapped[str] = mapped_column(String(16), default="prometida", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    demanda: Mapped[Demanda] = relationship()
