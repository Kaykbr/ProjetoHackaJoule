"""Central de operações: agente de campo, radar preditivo e otimizador de rotas."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.cidades import CIDADE_PADRAO, CidadeId
from app.config import settings
from app.database import get_db
from app.models import PontoDemanda
from app.schemas.ops import (
    Cenario,
    EstadoOut,
    PosicaoIn,
    PontoDemandaOut,
    RadarOut,
    RelatoIn,
    RelatoOut,
    RotaIn,
    RotaOut,
)
from app.seed_ops import seed_ops
from app.services import central, route_optimizer, voice_agent
from app.services.predictive_radar import calcular_radar

router = APIRouter(prefix="/ops", tags=["central de operações"])

_AUDIO_MAX_BYTES = 10 * 1024 * 1024
CidadeQ = Query(CIDADE_PADRAO, description="sp, rj ou for")


@router.get("/estado", response_model=EstadoOut)
def estado(cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> EstadoOut:
    """Base, pontos de demanda abertos, doadores e KPIs da cidade: tudo que o dashboard desenha."""
    return central.estado(db, cidade)


@router.post("/relatos", response_model=RelatoOut, status_code=status.HTTP_201_CREATED)
async def relato_texto(dados: RelatoIn, cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> RelatoOut:
    """Relato já transcrito (Web Speech API no navegador) ou digitado."""
    return await voice_agent.processar_relato(db, texto=dados.texto, cidade=cidade)


@router.post("/relatos/audio", response_model=RelatoOut, status_code=status.HTTP_201_CREATED)
async def relato_audio(
    arquivo: UploadFile = File(...), cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)
) -> RelatoOut:
    """Áudio gravado (quando o navegador não transcreve). Transcrição e extração pelo LLM."""
    tipo = (arquivo.content_type or "").split(";")[0]
    if not tipo.startswith("audio/"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Envie um arquivo de áudio.")
    conteudo = await arquivo.read(_AUDIO_MAX_BYTES + 1)
    if len(conteudo) > _AUDIO_MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Áudio maior que 10 MB.")
    return await voice_agent.processar_relato(db, audio=(tipo, conteudo), cidade=cidade)


@router.patch("/pontos/{ponto_id}", response_model=PontoDemandaOut)
def mover_ponto(ponto_id: int, dados: PosicaoIn, db: Session = Depends(get_db)) -> PontoDemandaOut:
    """Corrige o local de um ponto (ex.: o geocoding não achou e caiu no centro da cidade)."""
    ponto = db.get(PontoDemanda, ponto_id)
    if ponto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ponto não encontrado.")
    ponto.lat, ponto.lng = dados.lat, dados.lng
    db.commit()
    db.refresh(ponto)
    return central.ponto_out(ponto)


@router.get("/radar", response_model=RadarOut)
async def radar(
    cenario: Cenario = Query("normal"), cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)
) -> RadarOut:
    return await calcular_radar(central.pontos_abertos(db, cidade), cenario, cidade)


@router.post("/rotas", response_model=RotaOut, status_code=status.HTTP_201_CREATED)
async def gerar_rota(dados: RotaIn, cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> RotaOut:
    return await route_optimizer.planejar(db, dados, cidade)


@router.post("/rotas/{rota_id}/concluir", response_model=RotaOut)
def concluir_rota(rota_id: int, db: Session = Depends(get_db)) -> RotaOut:
    return route_optimizer.concluir(db, rota_id)


def _exigir_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Com ADMIN_TOKEN configurado (site público), só quem tem o token reinicia a demo."""
    if settings.admin_token and not secrets.compare_digest(x_admin_token or "", settings.admin_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só a organização da demo pode reiniciar os dados.")


@router.post("/reset", response_model=EstadoOut, dependencies=[Depends(_exigir_admin)])
def reset(cidade: CidadeId = CidadeQ, db: Session = Depends(get_db)) -> EstadoOut:
    """Volta a central da cidade aos dados de demonstração (útil antes do pitch)."""
    seed_ops(db, cidade)
    return central.estado(db, cidade)
