"""Schemas da central de operações. Espelhados em web/src/lib/types-ops.ts."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas import OrigemIA

CategoriaOps = Literal["alimentacao", "agasalho", "higiene", "saude"]
CATEGORIAS_OPS: tuple[str, ...] = ("alimentacao", "agasalho", "higiene", "saude")
Cenario = Literal["normal", "frente_fria", "tempestade", "onda_de_calor"]
ModoRota = Literal["atual", "preditivo"]


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ItemOps(BaseModel):
    categoria: CategoriaOps
    item: str = Field(min_length=1, max_length=80)
    quantidade: int = Field(ge=1, le=10_000)


class ItemRelato(ItemOps):
    #: Trecho do relato que justifica o item (conferido contra o texto antes de aceitar).
    evidencia: str = Field(default="", max_length=160)


class RelatoExtraido(BaseModel):
    """Saída estruturada do agente de campo (validada com Pydantic, venha do LLM ou das regras)."""

    local_referencia: str = Field(default="", max_length=160)
    bairro: str = Field(default="", max_length=80)
    pessoas: int | None = Field(default=None, ge=0, le=5_000)
    itens: list[ItemRelato] = Field(default_factory=list)
    urgencia: int = Field(default=3, ge=1, le=5)
    resumo: str = Field(default="", max_length=400)
    condicoes: list[str] = Field(default_factory=list)
    transcricao: str = Field(default="", max_length=4_000)

    @field_validator("condicoes")
    @classmethod
    def _condicoes(cls, v: list[str]) -> list[str]:
        return [c.strip().lower()[:30] for c in v if c and c.strip()][:8]


class PosicaoIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class RelatoIn(BaseModel):
    texto: str = Field(min_length=3, max_length=2_000)


class GeocodingOut(BaseModel):
    fonte: Literal["dicionario", "nominatim", "centro"]
    consulta: str
    lat: float
    lng: float


# ------------------------------------------------------------------ entidades


class BaseOut(_Base):
    id: int
    nome: str
    endereco: str
    lat: float
    lng: float


class PontoDemandaOut(_Base):
    id: int
    nome: str
    bairro: str
    lat: float
    lng: float
    pessoas: int
    urgencia: int
    resumo: str
    itens: list[ItemOps]
    condicoes: list[str]
    origem: str
    relatos_30d: int
    status: str
    transcricao: str
    atualizado_em: datetime
    total_itens: int


class DoadorOut(_Base):
    id: int
    nome: str
    tipo: str
    endereco: str
    lat: float
    lng: float
    estoque: list[ItemOps]
    total_itens: int


class KpisOut(BaseModel):
    pessoas_assistidas: int
    match_doacoes_pct: int
    kg_desperdicio_evitado: float
    co2_economizado_kg: float
    demandas_abertas: int
    rotas_concluidas: int


class EstadoOut(BaseModel):
    base: BaseOut
    demandas: list[PontoDemandaOut]
    doadores: list[DoadorOut]
    kpis: KpisOut
    llm_ativo: bool


class RelatoOut(BaseModel):
    acao: Literal["criado", "atualizado"]
    ponto: PontoDemandaOut
    extracao: RelatoExtraido
    geocoding: GeocodingOut
    fonte: str
    modelo: str
    offline: bool
    origem: OrigemIA
    pii_removidos: int
    descartados: int = 0
    aviso: str = ""


# ------------------------------------------------------------------ radar


class HoraPrevisao(BaseModel):
    hora: str
    temp: float
    chuva_prob: int
    vento_kmh: float


class PrevisaoOut(BaseModel):
    fonte: Literal["open-meteo", "simulacao", "padrao"]
    cenario: Cenario
    temp_agora: float
    temp_min_24h: float
    temp_max_24h: float
    chuva_prob_max: int
    chuva_mm_24h: float
    vento_max_kmh: float
    serie: list[HoraPrevisao]


class RiscoPontoOut(BaseModel):
    ponto_id: int
    risco_atual: int
    risco_24h: int
    nivel: Literal["baixo", "moderado", "alto", "critico"]
    fatores: list[str]
    demanda_projetada: list[ItemOps]


class AlertaOut(BaseModel):
    """PredictiveAlert."""

    id: str
    severidade: Literal["info", "atencao", "critico"]
    titulo: str
    descricao: str
    categoria: CategoriaOps | None = None
    aumento_pct: int | None = None
    pontos: list[int] = Field(default_factory=list)


class RadarOut(BaseModel):
    cenario: Cenario
    previsao: PrevisaoOut
    indice_clima: int
    riscos: list[RiscoPontoOut]
    alertas: list[AlertaOut]
    aumento_projetado: dict[str, int]


# ------------------------------------------------------------------ rotas


class RotaIn(BaseModel):
    modo: ModoRota = "atual"
    cenario: Cenario = "normal"
    max_entregas: int = Field(default=4, ge=1, le=8)


class ParadaOut(BaseModel):
    ordem: int
    tipo: Literal["base", "coleta", "entrega", "retorno"]
    ref_id: int
    nome: str
    lat: float
    lng: float
    itens: list[ItemOps]
    distancia_desde_anterior_km: float
    chegada_min: float


class PendenciaOut(BaseModel):
    ponto_id: int
    nome: str
    itens: list[ItemOps]


class RotaOut(BaseModel):
    """OptimizedRoute."""

    id: int
    modo: ModoRota
    cenario: Cenario
    status: Literal["planejada", "concluida"]
    fonte_rota: Literal["osrm", "estimativa"]
    paradas: list[ParadaOut]
    geometria: list[tuple[float, float]]
    distancia_km: float
    tempo_min: float
    taxa_atendimento_pct: int
    itens_entregues: int
    kg_entregues: float
    pessoas_atendidas: int
    co2_rota_kg: float
    co2_baseline_kg: float
    co2_evitado_kg: float
    #: Viagens individuais (doador → ponto) que a rota única substitui.
    viagens_evitadas: int
    nao_atendido: list[PendenciaOut]
    criada_em: datetime
