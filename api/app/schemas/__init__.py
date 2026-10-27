"""Schemas Pydantic de entrada e saída da API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.catalogo import SLUGS, normalizar_slug


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- cidades


class CenarioOut(BaseModel):
    id: str
    rotulo: str


class RelatoExemploOut(BaseModel):
    rotulo: str
    texto: str


class CidadeOut(BaseModel):
    id: str
    nome: str
    uf: str
    lat: float
    lng: float
    cenarios: list[CenarioOut]
    relatos_exemplo: list[RelatoExemploOut]


# ---------------------------------------------------------------- catálogo / ONGs


class CategoriaOut(_Base):
    slug: str
    nome: str
    sensivel_frio: bool
    sensivel_calor: bool


class OngOut(_Base):
    id: int
    nome: str
    descricao: str
    cidade: str
    contato_publico: str
    verificada: bool


class PontoIn(BaseModel):
    ong_id: int
    nome: str = Field(min_length=2, max_length=160)
    regiao: str = Field(min_length=2, max_length=80)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    referencia: str = Field(default="", max_length=240)
    modo_recebimento: Literal["entrega", "coleta"] = "entrega"


class PontoOut(_Base):
    id: int
    ong_id: int
    ong_nome: str
    nome: str
    regiao: str
    lat: float
    lng: float
    referencia: str
    modo_recebimento: str


# ---------------------------------------------------------------- demandas


class UrgenciaOut(_Base):
    score: int
    nivel: Literal["baixa", "media", "alta", "critica"]
    razoes: list[str]


class DemandaOut(_Base):
    id: int
    ponto: PontoOut
    categoria: str
    categoria_nome: str
    item: str
    quantidade: int
    quantidade_prometida: int
    quantidade_recebida: int
    faltam: int
    urgencia_base: int
    prazo: date | None
    status: str
    origem: str
    urgencia: UrgenciaOut
    created_at: datetime


class _ItemBase(BaseModel):
    categoria: str
    item: str = Field(min_length=1, max_length=120)
    quantidade: int = Field(ge=1, le=10_000)

    @field_validator("categoria")
    @classmethod
    def _categoria_valida(cls, v: str) -> str:
        slug = normalizar_slug(v)
        if slug not in SLUGS:
            raise ValueError("categoria desconhecida")
        return slug


class DemandaItemIn(_ItemBase):
    urgencia: int = Field(default=2, ge=1, le=3)
    prazo: date | None = None


class DemandasCreateIn(BaseModel):
    ponto_id: int
    origem: Literal["ia", "manual"] = "manual"
    itens: list[DemandaItemIn] = Field(min_length=1, max_length=30)


class DemandaStatusIn(BaseModel):
    status: Literal["aberta", "atendida", "cancelada"]


# ---------------------------------------------------------------- extração por IA


#: De onde veio a resposta: LLM, regras locais por decisão (cascata), cache, ou regras
#: locais porque a IA falhou/não está configurada.
OrigemIA = Literal["llm", "regras", "cache", "fallback"]


class ExtracaoIn(BaseModel):
    texto: str = Field(min_length=3, max_length=1500)


class ItemExtraido(BaseModel):
    categoria: str
    categoria_nome: str
    item: str
    quantidade: int
    quantidade_estimada: bool = False
    urgencia: int = 2
    prazo: date | None = None
    #: Trecho da mensagem que justifica o item (conferido contra o texto).
    evidencia: str = ""


class ExtracaoOut(BaseModel):
    itens: list[ItemExtraido]
    fonte: str
    modelo: str
    offline: bool
    origem: OrigemIA
    pii_removidos: int
    #: Itens que o modelo devolveu sem evidência no texto e foram descartados.
    descartados: int = 0
    aviso: str = ""


# ---------------------------------------------------------------- doador


class ItemOfertaIn(_ItemBase):
    pass


class SugestoesIn(BaseModel):
    itens: list[ItemOfertaIn] = Field(min_length=1, max_length=20)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class OpcaoOut(BaseModel):
    demanda: DemandaOut
    distancia_km: float
    score: int
    quantidade_sugerida: int
    razoes: list[str]


class SugestaoOut(BaseModel):
    item: ItemOfertaIn
    opcoes: list[OpcaoOut]


class DoacaoIn(BaseModel):
    demanda_id: int
    quantidade: int = Field(ge=1, le=10_000)
    doador_apelido: str = Field(default="Anônimo", max_length=60)


class DoacaoOut(BaseModel):
    id: int
    demanda: DemandaOut
    quantidade: int
    doador_apelido: str
    status: str
    created_at: datetime


class DoacaoStatusIn(BaseModel):
    status: Literal["entregue", "cancelada"]


# ---------------------------------------------------------------- clima / impacto


class SimulacaoIn(BaseModel):
    temp_min: float = Field(ge=-20, le=45)
    temp_max: float = Field(default=18, ge=-20, le=50)


class ClimaRegiaoOut(BaseModel):
    regiao: str
    temp_min: float | None
    temp_max: float | None
    fonte: str


class ClimaOut(BaseModel):
    simulacao: bool
    regioes: list[ClimaRegiaoOut]
    alertas: list[str]


class UsoIaOut(BaseModel):
    llm_ativo: bool
    provider: str
    modelo: str
    #: Mensagens processadas (todas as origens).
    chamadas: int
    #: Mensagens resolvidas sem IA remota (regras + cache + fallback).
    chamadas_offline: int
    chamadas_llm: int
    resolvidas_regras: int
    cache_hits: int
    fallback: int
    itens_sem_evidencia: int
    tokens: int
    custo_estimado_usd: float
    custo_medio_usd: float
    pii_removidos: int


class ImpactoOut(BaseModel):
    ongs: int
    pontos: int
    demandas_abertas: int
    demandas_atendidas: int
    itens_prometidos: int
    itens_entregues: int
    doacoes: int
    ia: UsoIaOut
