"""Engine, sessão e Base declarativa do SQLAlchemy."""
from __future__ import annotations

from collections.abc import Iterator

from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#: Colunas adicionadas depois da primeira versão do schema.
#: `create_all` cria tabelas novas, mas não altera tabelas existentes — daí esta lista.
#: Só mudanças ADITIVAS; renomear/remover coluna ou migrar dados pede Alembic.
_CIDADE = {"cidade_id": "VARCHAR(8) NOT NULL DEFAULT 'sp'"}
_ADDITIVE_COLUMNS: dict[str, dict[str, str]] = {
    "ongs": _CIDADE,
    "ops_bases": _CIDADE,
    "ops_pontos_demanda": _CIDADE,
    "ops_doadores": _CIDADE,
    "ops_rotas": _CIDADE,
    "ai_logs": {
        "origem": "VARCHAR(16) NOT NULL DEFAULT 'llm'",
        "descartados": "INTEGER NOT NULL DEFAULT 0",
    },
}


def _apply_additive_columns() -> None:
    inspector = inspect(engine)
    existentes = set(inspector.get_table_names())
    with engine.begin() as conexao:
        for tabela, colunas in _ADDITIVE_COLUMNS.items():
            if tabela not in existentes:
                continue
            presentes = {c["name"] for c in inspector.get_columns(tabela)}
            for nome, ddl in colunas.items():
                if nome not in presentes:
                    conexao.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {nome} {ddl}"))
                    logger.info("Schema atualizado: {}.{} adicionada.", tabela, nome)


def init_db() -> None:
    """Cria tabelas novas e aplica colunas aditivas pendentes."""
    from app import models  # noqa: F401  (registra os modelos no metadata)

    Base.metadata.create_all(bind=engine)
    _apply_additive_columns()
