from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

# Antes de importar o app: banco temporário, sem IA remota e sem rede de clima.
_DB = Path(tempfile.gettempdir()) / "doacerto_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"
os.environ["LLM_PROVIDER"] = "offline"
os.environ["CLIMA_ENABLED"] = "false"
os.environ["NOMINATIM_ENABLED"] = "false"
os.environ["OSRM_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import limites, seed  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.llm import cache  # noqa: E402
from app.services import clima, extracao, voice_agent  # noqa: E402


@pytest.fixture(autouse=True)
def _banco_limpo() -> Iterator[None]:
    seed.run()
    limites.limpar()
    clima.limpar_simulacao()
    cache.respostas.limpar()
    extracao._client = None
    voice_agent._client = None
    yield
    clima.limpar_simulacao()
    extracao._client = None
    voice_agent._client = None


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session
