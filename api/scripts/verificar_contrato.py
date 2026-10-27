"""Confere se o JSON da API bate com as interfaces de web/src/lib/types-ops.ts e types.ts.

Precisa da API rodando em localhost:8000. Faz reset da central de cada cidade no início e no fim.
Uso: python -m scripts.verificar_contrato
"""
import re

import httpx
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web" / "src" / "lib"
interfaces = {}
for arquivo in ("types.ts", "types-ops.ts"):
    ts = (WEB / arquivo).read_text(encoding="utf-8")
    for nome, pai, corpo in re.findall(r"export interface (\w+)(?: extends (\w+))? \{(.*?)\n\}", ts, re.S):
        # A interface-pai aparece antes no arquivo (ex.: ItemRelato extends ItemOps).
        interfaces[nome] = interfaces.get(pai, set()) | {m for m in re.findall(r"^\s+(\w+)\??:", corpo, re.M)}
B = "http://localhost:8000"
c = httpx.Client(timeout=60)
problemas = []
def checar(nome, obj):
    esperado, real = interfaces[nome], set(obj)
    if esperado != real:
        problemas.append(f"{nome}: faltam no JSON {esperado - real or '-'}; sobram {real - esperado or '-'}")

checar("CidadeDetalhe", c.get(B + "/cidades").json()[0])
# Um relato com lugar conhecido de cada cidade; o cenário de clima varia junto.
CASOS = {
    "sp": ("Vale do Anhangabaú, 5 pessoas, 5 marmitas", "tempestade"),
    "rj": ("Arcos da Lapa, 6 pessoas, 6 marmitas", "tempestade"),
    "for": ("Praça do Ferreira, 4 pessoas, 4 marmitas", "onda_de_calor"),
}
for cidade, (relato, cenario) in CASOS.items():
    q = {"cidade": cidade}
    estado = c.post(B + "/ops/reset", params=q).json()
    checar("EstadoOps", estado); checar("BaseOps", estado["base"]); checar("KpisOps", estado["kpis"])
    checar("PontoDemanda", estado["demandas"][0]); checar("Doador", estado["doadores"][0]); checar("ItemOps", estado["doadores"][0]["estoque"][0])
    r = c.post(B + "/ops/relatos", params=q, json={"texto": relato}).json()
    checar("RelatoResultado", r); checar("RelatoExtraido", r["extracao"]); checar("ItemRelato", r["extracao"]["itens"][0])
    if r["geocoding"]["fonte"] != "dicionario":
        problemas.append(f"{cidade}: relato '{relato}' não foi achado no dicionário da cidade")
    rad = c.get(B + "/ops/radar", params={**q, "cenario": cenario}).json()
    checar("Radar", rad); checar("Previsao", rad["previsao"]); checar("HoraPrevisao", rad["previsao"]["serie"][0])
    checar("RiscoPonto", rad["riscos"][0]); checar("AlertaPreditivo", rad["alertas"][0])
    rota = c.post(B + "/ops/rotas", params=q, json={"modo": "atual", "max_entregas": 4}).json()
    checar("RotaOtimizada", rota); checar("Parada", rota["paradas"][1])
    c.post(B + "/ops/reset", params=q)
print("\n".join(problemas) or f"OK: {len(interfaces)} interfaces e {len(CASOS)} cidades conferidas contra respostas reais")
