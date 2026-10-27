from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.llm.client import BaseLLMClient, Completion, LLMClient
from app.llm.providers.offline import OfflineProvider
from app.models import AiLog
from app.services import extracao

SE = (-23.5503, -46.6340)


def _ponto_id(client: TestClient, nome: str) -> int:
    return next(p["id"] for p in client.get("/pontos").json() if p["nome"] == nome)


def test_extrair_demanda_offline_registra_uso_e_remove_pii(client: TestClient, db) -> None:
    r = client.post(
        "/demandas/extrair",
        json={"texto": "Precisamos de 30 cobertores e 15 sabonetes. Contato: (11) 91234-5678"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["offline"] is True
    assert body["pii_removidos"] == 1
    assert {(i["categoria"], i["quantidade"]) for i in body["itens"]} == {
        ("cobertor", 30),
        ("higiene", 15),
    }
    log = db.query(AiLog).one()
    assert log.offline is True and log.custo_estimado_usd == 0


def test_extrair_demanda_quantidade_nao_dita_vira_estimativa(client: TestClient) -> None:
    itens = client.post("/demandas/extrair", json={"texto": "precisamos de agasalhos"}).json()["itens"]
    assert itens[0]["quantidade"] == 10
    assert itens[0]["quantidade_estimada"] is True


class _JsonQuebrado(BaseLLMClient):
    name = "fake"
    model = "fake-1"

    def generate(self, prompt: str, *, system: str = "", schema: dict[str, Any] | None = None, midia: Any = None, metadata: dict[str, Any] | None = None) -> Completion:
        return Completion(texto="Claro! Aqui estão os itens: cobertores", tokens_entrada=50, tokens_saida=8)


def test_json_invalido_do_llm_cai_no_parser_local(client: TestClient) -> None:
    extracao._client = LLMClient(_JsonQuebrado(), fallback=OfflineProvider())
    body = client.post("/ofertas/extrair", json={"texto": "tenho 3 casacos"}).json()
    assert body["offline"] is True
    assert body["itens"][0]["categoria"] == "agasalho"
    assert body["itens"][0]["quantidade"] == 3


def test_fluxo_completo_publicar_sugerir_prometer_entregar(client: TestClient) -> None:
    ponto = _ponto_id(client, "Praça da Sé")
    publicadas = client.post(
        "/demandas",
        json={"ponto_id": ponto, "origem": "ia", "itens": [
            {"categoria": "calcado", "item": "chinelo", "quantidade": 5, "urgencia": 3}
        ]},
    )
    assert publicadas.status_code == 201
    demanda = publicadas.json()[0]

    sugestoes = client.post(
        "/ofertas/sugestoes",
        json={"lat": SE[0], "lng": SE[1], "itens": [{"categoria": "calcado", "item": "chinelo", "quantidade": 8}]},
    ).json()
    melhor = sugestoes[0]["opcoes"][0]
    assert melhor["demanda"]["id"] == demanda["id"]
    assert melhor["quantidade_sugerida"] == 5
    assert any("completa o pedido" in r for r in melhor["razoes"])

    doacao = client.post("/doacoes", json={"demanda_id": demanda["id"], "quantidade": 8}).json()
    assert doacao["quantidade"] == 5  # limitado ao que falta
    assert client.post("/doacoes", json={"demanda_id": demanda["id"], "quantidade": 1}).status_code == 409

    entregue = client.patch(f"/doacoes/{doacao['id']}", json={"status": "entregue"}).json()
    assert entregue["demanda"]["status"] == "atendida"
    assert entregue["demanda"]["quantidade_recebida"] == 5

    impacto = client.get("/impacto").json()
    assert impacto["itens_entregues"] == 5
    assert impacto["demandas_atendidas"] == 1


def test_cancelar_doacao_libera_quantidade(client: TestClient) -> None:
    demanda = client.get("/demandas", params={"categoria": "roupa"}).json()[0]
    antes = demanda["faltam"]
    doacao = client.post("/doacoes", json={"demanda_id": demanda["id"], "quantidade": 3}).json()
    assert doacao["demanda"]["faltam"] == antes - 3
    cancelada = client.patch(f"/doacoes/{doacao['id']}", json={"status": "cancelada"}).json()
    assert cancelada["demanda"]["faltam"] == antes


def test_simulacao_de_frio_reordena_prioridades(client: TestClient) -> None:
    def score_casaco() -> int:
        return next(d["urgencia"]["score"] for d in client.get("/demandas").json() if d["item"] == "casaco")

    normal = score_casaco()
    estado = client.post("/clima/simulacao", json={"temp_min": 6}).json()
    assert estado["simulacao"] is True
    assert estado["alertas"]
    assert score_casaco() == normal + 25

    client.delete("/clima/simulacao")
    assert score_casaco() == normal


def test_validacao_rejeita_categoria_vazia(client: TestClient) -> None:
    r = client.post("/demandas", json={"ponto_id": 1, "itens": []})
    assert r.status_code == 422
    assert "itens" in r.json()["detail"]
