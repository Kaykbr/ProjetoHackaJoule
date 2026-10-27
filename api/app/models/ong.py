from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Ong(Base):
    __tablename__ = "ongs"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    descricao: Mapped[str] = mapped_column(Text, default="")
    cidade: Mapped[str] = mapped_column(String(80), default="São Paulo")
    #: Id da cidade em app/cidades.py ("sp", "rj", "for"): filtra tudo que é da ONG.
    cidade_id: Mapped[str] = mapped_column(String(8), default="sp", index=True)
    contato_publico: Mapped[str] = mapped_column(String(160), default="")
    verificada: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pontos: Mapped[list[Ponto]] = relationship(back_populates="ong", cascade="all, delete-orphan")


class Ponto(Base):
    """Ponto de atendimento/distribuição de uma ONG (praça, sede, abrigo).

    Nunca representa a localização de uma pessoa — só locais onde a ONG atua.
    """

    __tablename__ = "pontos"

    id: Mapped[int] = mapped_column(primary_key=True)
    ong_id: Mapped[int] = mapped_column(ForeignKey("ongs.id"), index=True)
    nome: Mapped[str] = mapped_column(String(160))
    regiao: Mapped[str] = mapped_column(String(80))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    referencia: Mapped[str] = mapped_column(String(240), default="")
    #: Como o doador entrega: "coleta" (ONG busca) ou "entrega" (doador leva ao ponto).
    modo_recebimento: Mapped[str] = mapped_column(String(16), default="entrega")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ong: Mapped[Ong] = relationship(back_populates="pontos")
