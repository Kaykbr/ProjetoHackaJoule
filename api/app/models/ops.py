"""Central de operações (Fase 2): base da ONG, pontos de demanda, doadores e rotas.

Itens e estoques ficam em JSON (`[{categoria, item, quantidade}]`): cada ponto tem poucos
itens e eles mudam juntos, então uma tabela à parte só adicionaria joins.
Como no resto do sistema, um ponto de demanda é um LOCAL relatado por voluntários, nunca uma pessoa.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BaseOperacional(Base):
    """Ponto de partida das rotas (sede/garagem da ONG)."""

    __tablename__ = "ops_bases"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Id da cidade em app/cidades.py ("sp", "rj", "for").
    cidade_id: Mapped[str] = mapped_column(String(8), default="sp", index=True)
    nome: Mapped[str] = mapped_column(String(160))
    endereco: Mapped[str] = mapped_column(String(240), default="")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)


class PontoDemanda(Base):
    """DemandPoint: local onde voluntários relataram necessidades."""

    __tablename__ = "ops_pontos_demanda"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Id da cidade em app/cidades.py ("sp", "rj", "for").
    cidade_id: Mapped[str] = mapped_column(String(8), default="sp", index=True)
    nome: Mapped[str] = mapped_column(String(160))
    bairro: Mapped[str] = mapped_column(String(80), default="")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    pessoas: Mapped[int] = mapped_column(Integer, default=0)
    #: 1 (baixa) a 5 (emergência).
    urgencia: Mapped[int] = mapped_column(Integer, default=3)
    resumo: Mapped[str] = mapped_column(Text, default="")
    itens: Mapped[list] = mapped_column(JSON, default=list)
    condicoes: Mapped[list] = mapped_column(JSON, default=list)
    #: "seed" | "voz" | "texto"
    origem: Mapped[str] = mapped_column(String(16), default="seed")
    #: Histórico usado pelo radar: quantos relatos este ponto recebeu nos últimos 30 dias.
    relatos_30d: Mapped[int] = mapped_column(Integer, default=1)
    transcricao: Mapped[str] = mapped_column(Text, default="")
    #: "aberto" | "atendido"
    status: Mapped[str] = mapped_column(String(16), default="aberto", index=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Doador(Base):
    """SupplyDonor: comércio, igreja ou condomínio com itens prontos para coleta."""

    __tablename__ = "ops_doadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Id da cidade em app/cidades.py ("sp", "rj", "for").
    cidade_id: Mapped[str] = mapped_column(String(8), default="sp", index=True)
    nome: Mapped[str] = mapped_column(String(160))
    tipo: Mapped[str] = mapped_column(String(40), default="comercio")
    endereco: Mapped[str] = mapped_column(String(240), default="")
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    estoque: Mapped[list] = mapped_column(JSON, default=list)


class RotaOtimizada(Base):
    """OptimizedRoute: plano gerado pelo otimizador. Concluída, atualiza estoques e demandas."""

    __tablename__ = "ops_rotas"

    id: Mapped[int] = mapped_column(primary_key=True)
    #: Id da cidade em app/cidades.py ("sp", "rj", "for").
    cidade_id: Mapped[str] = mapped_column(String(8), default="sp", index=True)
    modo: Mapped[str] = mapped_column(String(16), default="atual")
    cenario: Mapped[str] = mapped_column(String(24), default="normal")
    #: "planejada" | "concluida"
    status: Mapped[str] = mapped_column(String(16), default="planejada", index=True)
    plano: Mapped[dict] = mapped_column(JSON)
    distancia_km: Mapped[float] = mapped_column(Float, default=0)
    co2_evitado_kg: Mapped[float] = mapped_column(Float, default=0)
    itens_entregues: Mapped[int] = mapped_column(Integer, default=0)
    kg_entregues: Mapped[float] = mapped_column(Float, default=0)
    pessoas_atendidas: Mapped[int] = mapped_column(Integer, default=0)
    criada_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
