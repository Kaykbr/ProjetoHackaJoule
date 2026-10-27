"""Central de operações: agente de campo, radar e rotas (sem rede: testa os fallbacks)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.route_optimizer import ordenar, substitui


def _estado(client: TestClient) -> dict:
    return client.get("/ops/estado").json()


def test_estado_inicial_vem_do_seed(client: TestClient) -> None:
    estado = _estado(client)
    assert len(estado["demandas"]) == 5
    assert len(estado["doadores"]) == 6
    assert estado["base"]["nome"]
    assert 0 < estado["kpis"]["match_doacoes_pct"] <= 100
    assert estado["kpis"]["pessoas_assistidas"] == 0


def test_relato_cria_ponto_geocodificado_e_sem_dados_pessoais(client: TestClient) -> None:
    r = client.post("/ops/relatos", json={"texto": (
        "Estamos no Vale do Anhangabaú, chovendo forte, 18 pessoas, precisamos urgente de "
        "18 cobertores, 20 marmitas e 5 kits de higiene. Me liga no (11) 98888-7777"
    )})
    assert r.status_code == 201
    body = r.json()
    assert body["acao"] == "criado"
    assert body["geocoding"]["fonte"] == "dicionario"
    assert body["ponto"]["nome"] == "Vale do Anhangabaú"
    assert body["pii_removidos"] == 1
    assert "98888" not in body["ponto"]["transcricao"]
    assert body["extracao"]["pessoas"] == 18
    assert body["extracao"]["urgencia"] >= 4
    assert "chuva" in body["extracao"]["condicoes"]
    assert {(i["categoria"], i["quantidade"]) for i in body["ponto"]["itens"]} == {
        ("agasalho", 18), ("alimentacao", 20), ("higiene", 5),
    }
    assert len(_estado(client)["demandas"]) == 6


def test_relato_no_mesmo_local_atualiza_o_ponto(client: TestClient) -> None:
    antes = next(p for p in _estado(client)["demandas"] if p["nome"] == "Praça da Sé")
    body = client.post("/ops/relatos", json={"texto": "Praça da Sé de novo: agora precisam de 8 lonas"}).json()
    assert body["acao"] == "atualizado"
    assert body["ponto"]["id"] == antes["id"]
    assert body["ponto"]["relatos_30d"] == antes["relatos_30d"] + 1
    assert any(i["item"] == "lona" and i["quantidade"] == 8 for i in body["ponto"]["itens"])
    assert len(_estado(client)["demandas"]) == 5


def test_local_desconhecido_vai_para_o_centro_com_aviso(client: TestClient) -> None:
    body = client.post("/ops/relatos", json={"texto": "Tem 4 pessoas precisando de 4 marmitas"}).json()
    assert body["geocoding"]["fonte"] == "centro"
    assert "local" in body["aviso"].lower()


def test_audio_sem_ia_explica_o_que_fazer(client: TestClient) -> None:
    r = client.post("/ops/relatos/audio", files={"arquivo": ("relato.webm", b"\x1a\x45\xdf\xa3", "audio/webm")})
    assert r.status_code == 503
    assert "microfone" in r.json()["detail"]


def test_radar_reage_aos_cenarios(client: TestClient) -> None:
    normal = client.get("/ops/radar").json()
    frio = client.get("/ops/radar", params={"cenario": "frente_fria"}).json()
    tempestade = client.get("/ops/radar", params={"cenario": "tempestade"}).json()

    assert normal["previsao"]["fonte"] == "padrao"
    assert frio["previsao"]["fonte"] == "simulacao"
    assert frio["previsao"]["temp_min_24h"] <= 6
    assert frio["indice_clima"] > normal["indice_clima"]
    assert frio["aumento_projetado"]["agasalho"] >= 50
    assert any(a["id"] == "frio" for a in frio["alertas"])
    assert any(a["id"] == "chuva" for a in tempestade["alertas"])

    risco = lambda radar: {r["ponto_id"]: r["risco_24h"] for r in radar["riscos"]}  # noqa: E731
    assert all(risco(frio)[pid] >= v for pid, v in risco(normal).items())
    assert any(r["nivel"] == "critico" for r in frio["riscos"])


def test_rota_coleta_antes_de_entregar_e_concluir_atualiza_tudo(client: TestClient) -> None:
    rota = client.post("/ops/rotas", json={"modo": "atual", "max_entregas": 3}).json()
    tipos = [p["tipo"] for p in rota["paradas"]]
    assert tipos[0] == "base" and tipos[-1] == "retorno"
    assert tipos.index("entrega") > max(i for i, t in enumerate(tipos) if t == "coleta")
    assert rota["fonte_rota"] == "estimativa"
    assert len(rota["geometria"]) == len(rota["paradas"])
    assert rota["distancia_km"] > 0 and rota["tempo_min"] > 0
    assert 0 < rota["taxa_atendimento_pct"] <= 100
    assert rota["co2_evitado_kg"] == round(max(0, rota["co2_baseline_kg"] - rota["co2_rota_kg"]), 2)
    assert rota["viagens_evitadas"] >= 1
    # Substituição só entre equivalentes: nenhuma entrega troca marmita por água.
    pedidos = {p["id"]: {i["item"] for i in p["itens"]} for p in _estado(client)["demandas"]}
    for parada in rota["paradas"]:
        if parada["tipo"] == "entrega":
            for item in parada["itens"]:
                assert any(substitui(pedido, item["item"]) for pedido in pedidos[parada["ref_id"]])
    coletado = sum(i["quantidade"] for p in rota["paradas"] if p["tipo"] == "coleta" for i in p["itens"])
    entregue = sum(i["quantidade"] for p in rota["paradas"] if p["tipo"] == "entrega" for i in p["itens"])
    assert coletado == entregue == rota["itens_entregues"]

    estoque_antes = sum(d["total_itens"] for d in _estado(client)["doadores"])
    feita = client.post(f"/ops/rotas/{rota['id']}/concluir").json()
    assert feita["status"] == "concluida"
    estado = _estado(client)
    assert sum(d["total_itens"] for d in estado["doadores"]) == estoque_antes - coletado
    assert estado["kpis"]["pessoas_assistidas"] == rota["pessoas_atendidas"] > 0
    assert estado["kpis"]["rotas_concluidas"] == 1
    assert client.post(f"/ops/rotas/{rota['id']}/concluir").status_code == 409


def test_rota_preditiva_na_tempestade_pede_lona_que_ninguem_tem(client: TestClient) -> None:
    rota = client.post("/ops/rotas", json={"modo": "preditivo", "cenario": "tempestade", "max_entregas": 4}).json()
    faltando = {i["item"] for p in rota["nao_atendido"] for i in p["itens"]}
    assert "lona" in faltando
    assert rota["taxa_atendimento_pct"] < 100


def test_reset_volta_ao_seed(client: TestClient) -> None:
    client.post("/ops/relatos", json={"texto": "Vale do Anhangabaú com 5 pessoas e 5 marmitas"})
    assert len(_estado(client)["demandas"]) == 6
    assert len(client.post("/ops/reset").json()["demandas"]) == 5


def test_ordenar_resolve_caminho_com_2opt() -> None:
    # Pontos em linha: a ordem ótima saindo de 0 é 1, 2, 3, 4.
    pontos = [(0.0, 0.03), (0.0, 0.01), (0.0, 0.04), (0.0, 0.02)]
    ordem = ordenar((0.0, 0.0), pontos, lambda p: p)
    assert ordem == sorted(pontos, key=lambda p: p[1])


def test_ponto_urgente_sem_estoque_nao_trava_a_rota_e_acento_nao_importa(client: TestClient, db) -> None:
    # Estado visto ao testar a demo: os pontos mais urgentes pedem só o que acabou no estoque,
    # e o LLM devolveu "agua" (sem acento) enquanto o doador tem "garrafa de água".
    from app.models import PontoDemanda

    for ponto in db.query(PontoDemanda).all():
        ponto.itens = [{"categoria": "agasalho", "item": "lona", "quantidade": 5}]  # ninguém tem lona
    db.add(PontoDemanda(nome="Viaduto Pacaembu", bairro="Pacaembu", lat=-23.527, lng=-46.661, pessoas=7,
                        urgencia=1, itens=[{"categoria": "alimentacao", "item": "agua", "quantidade": 7}]))
    db.commit()

    r = client.post("/ops/rotas", json={"modo": "atual", "max_entregas": 2})
    assert r.status_code == 201
    rota = r.json()
    entregas = [p for p in rota["paradas"] if p["tipo"] == "entrega"]
    assert [p["nome"] for p in entregas] == ["Viaduto Pacaembu"]
    assert entregas[0]["itens"][0]["item"] == "garrafa de água"
    assert any(i["item"] == "lona" for p in rota["nao_atendido"] for i in p["itens"])
