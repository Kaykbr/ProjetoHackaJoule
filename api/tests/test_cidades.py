"""Três cidades (SP, RJ, Fortaleza) e as proteções do site público."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.llm.client import LLMClient
from app.llm.providers.offline import OfflineProvider
from app.services import extracao
from tests.test_ia import _SO_MARMITAS, _Roteiro


def _estado(client: TestClient, cidade: str) -> dict:
    return client.get("/ops/estado", params={"cidade": cidade}).json()


# ------------------------------------------------------------------ cidades


def test_lista_as_tres_cidades_com_cenarios_plausiveis(client: TestClient) -> None:
    cidades = {c["id"]: c for c in client.get("/cidades").json()}
    assert set(cidades) == {"sp", "rj", "for"}
    cenarios = lambda cid: {c["id"] for c in cidades[cid]["cenarios"]}  # noqa: E731
    assert "frente_fria" in cenarios("sp")
    assert "frente_fria" not in cenarios("for")
    assert "onda_de_calor" in cenarios("for")
    assert all(len(c["relatos_exemplo"]) >= 3 for c in cidades.values())


def test_cada_cidade_tem_sua_central(client: TestClient) -> None:
    sp, rj, fortaleza = (_estado(client, c) for c in ("sp", "rj", "for"))
    ids = [{p["id"] for p in e["demandas"]} for e in (sp, rj, fortaleza)]
    assert all(ids) and not (ids[0] & ids[1] or ids[1] & ids[2] or ids[0] & ids[2])
    assert sp["base"]["lat"] < -23 < rj["base"]["lat"] < -22 and -4 < fortaleza["base"]["lat"] < -3


def test_site_publico_filtra_por_cidade(client: TestClient) -> None:
    for cidade in ("sp", "rj", "for"):
        pontos = client.get("/pontos", params={"cidade": cidade}).json()
        assert pontos, cidade
        assert client.get("/demandas", params={"cidade": cidade}).json(), cidade
    impacto_sp = client.get("/impacto", params={"cidade": "sp"}).json()
    impacto_rj = client.get("/impacto", params={"cidade": "rj"}).json()
    assert impacto_sp["ongs"] > 0 and impacto_rj["ongs"] > 0
    assert impacto_sp["pontos"] != impacto_rj["pontos"] or impacto_sp["ongs"] != impacto_rj["ongs"]


def test_cidade_desconhecida_e_recusada(client: TestClient) -> None:
    assert client.get("/ops/estado", params={"cidade": "xx"}).status_code == 422


def test_relato_no_rio_usa_o_dicionario_do_rio(client: TestClient) -> None:
    antes = len(_estado(client, "sp")["demandas"])
    body = client.post("/ops/relatos", params={"cidade": "rj"},
                       json={"texto": "Arcos da Lapa, 12 pessoas, precisam de 12 marmitas"}).json()
    assert body["geocoding"]["fonte"] == "dicionario"
    assert body["ponto"]["nome"] == "Arcos da Lapa"
    assert -23 < body["ponto"]["lat"] < -22.8
    assert len(_estado(client, "sp")["demandas"]) == antes  # SP não foi tocada


def test_rota_sai_da_base_da_cidade(client: TestClient) -> None:
    base = _estado(client, "for")["base"]
    rota = client.post("/ops/rotas", params={"cidade": "for"}, json={"modo": "atual", "max_entregas": 3}).json()
    inicio = rota["paradas"][0]
    assert inicio["tipo"] == "base"
    assert (inicio["lat"], inicio["lng"]) == (base["lat"], base["lng"])


def test_onda_de_calor_pede_agua(client: TestClient) -> None:
    normal = client.get("/ops/radar", params={"cidade": "for"}).json()
    calor = client.get("/ops/radar", params={"cidade": "for", "cenario": "onda_de_calor"}).json()
    assert calor["previsao"]["temp_max_24h"] >= 36
    assert calor["indice_clima"] > normal["indice_clima"]
    assert any(a["id"] == "calor" for a in calor["alertas"])
    itens = {i["item"] for r in calor["riscos"] for i in r["demanda_projetada"]}
    assert "garrafa de água" in itens


def test_arrastar_o_marcador_salva_o_local(client: TestClient) -> None:
    ponto = _estado(client, "sp")["demandas"][0]
    r = client.patch(f"/ops/pontos/{ponto['id']}", json={"lat": -23.5, "lng": -46.6})
    assert r.status_code == 200
    assert (r.json()["lat"], r.json()["lng"]) == (-23.5, -46.6)
    assert client.patch("/ops/pontos/999999", json={"lat": -23.5, "lng": -46.6}).status_code == 404


# ------------------------------------------------------------------ proteções


def test_excesso_de_mensagens_recebe_429(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "limite_ia_por_minuto", 2)
    corpo = {"texto": "precisamos de 10 cobertores"}
    assert client.post("/demandas/extrair", json=corpo).status_code == 200
    assert client.post("/demandas/extrair", json=corpo).status_code == 200
    r = client.post("/demandas/extrair", json=corpo)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    # Outro visitante (outro IP, posto pelo proxy no fim da lista) não é afetado...
    assert client.post("/demandas/extrair", json=corpo, headers={"X-Forwarded-For": "10.0.0.9"}).status_code == 200
    # ...mas inventar um IP no começo do cabeçalho não engana o limite.
    for falso in ("1.1.1.1", "2.2.2.2"):
        r = client.post("/demandas/extrair", json=corpo, headers={"X-Forwarded-For": f"{falso}, 10.0.0.9"})
    assert r.status_code == 429


def test_teto_diario_cai_no_fallback_sem_chamar_o_llm(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "cascata_enabled", False)
    monkeypatch.setattr(settings, "llm_max_chamadas_dia", 0)
    fake = _Roteiro(_SO_MARMITAS)
    extracao._client = LLMClient(fake, fallback=OfflineProvider())
    body = client.post("/demandas/extrair", json={"texto": "precisamos de 15 marmitas"}).json()
    assert fake.chamadas == 0
    assert body["origem"] == "fallback"
    assert body["itens"]


def test_reset_exige_token_quando_configurado(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "segredo-da-demo")
    assert client.post("/ops/reset").status_code == 403
    assert client.post("/ops/reset", headers={"X-Admin-Token": "errado"}).status_code == 403
    assert client.post("/ops/reset", headers={"X-Admin-Token": "segredo-da-demo"}).status_code == 200


def test_atras_de_vercel_e_render_vale_o_penultimo_ip(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Vercel põe o visitante; o Render acrescenta o IP da Vercel no fim.
    monkeypatch.setattr(settings, "proxies_confiaveis", 2)
    monkeypatch.setattr(settings, "limite_ia_por_minuto", 1)
    corpo = {"texto": "precisamos de 10 cobertores"}
    assert client.post("/demandas/extrair", json=corpo, headers={"X-Forwarded-For": "7.7.7.7, 76.76.21.1"}).status_code == 200
    # Outro visitante, mesmo IP da Vercel: não é bloqueado.
    assert client.post("/demandas/extrair", json=corpo, headers={"X-Forwarded-For": "8.8.8.8, 76.76.21.1"}).status_code == 200
    assert client.post("/demandas/extrair", json=corpo, headers={"X-Forwarded-For": "7.7.7.7, 76.76.21.1"}).status_code == 429


def test_diagnostico_de_ip_so_com_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_token", "segredo-da-demo")
    monkeypatch.setattr(settings, "proxies_confiaveis", 2)
    cab = {"X-Forwarded-For": "7.7.7.7, 76.76.21.1"}
    assert "ip_detectado" not in client.get("/health", headers=cab).json()
    corpo = client.get("/health", headers={**cab, "X-Admin-Token": "segredo-da-demo"}).json()
    assert corpo["ip_detectado"] == "7.7.7.7"
