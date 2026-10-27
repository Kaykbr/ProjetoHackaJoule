"""Entrypoint da API do Doa Certo."""
from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.database import init_db
from app.limites import LimiteIA
from app.routes import clima, demandas, doacoes, ongs, ops

logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | {level: <8} | {message}")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    logger.info(
        "Doa Certo API pronta | db={} | llm={} | clima={}",
        settings.database_url.split("://")[0],
        settings.provider_efetivo,
        "open-meteo" if settings.clima_enabled else "desligado",
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Conecta doadores a demandas reais de ONGs que atendem pessoas em situação de rua. "
        "IA só para transformar texto em dados; urgência e matching são regras explicáveis."
    ),
    lifespan=lifespan,
)

app.add_middleware(LimiteIA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Devolve a primeira mensagem de validação em `detail`, que é o que a UI exibe."""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(part) for part in first.get("loc", [])[1:]) or "campo"
    message = first.get("msg", "Dados inválidos.").replace("Value error, ", "")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": f"{field}: {message}", "errors": exc.errors()}),
    )


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_enabled": settings.llm_enabled,
        "clima_enabled": settings.clima_enabled,
    }


app.include_router(ongs.router)
app.include_router(demandas.router)
app.include_router(doacoes.router)
app.include_router(clima.router)
app.include_router(ops.router)
