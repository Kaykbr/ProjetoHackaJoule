"""Dados de demonstração da central de operações: São Paulo, Rio de Janeiro e Fortaleza.

Doadores e bases são FICTÍCIOS. Os pontos de demanda são praças e viadutos públicos onde
ONGs costumam atuar; nenhum dado de pessoa é cadastrado.
"""
from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.cidades import CIDADES
from app.models import BaseOperacional, Doador, PontoDemanda, RotaOtimizada


def _itens(*trios: tuple[str, str, int]) -> list[dict]:
    return [{"categoria": c, "item": i, "quantidade": q} for c, i, q in trios]


BASES: dict[str, dict] = {
    "sp": {"nome": "Galpão da Rede Calor Humano", "endereco": "Cambuci, São Paulo (fictício)", "lat": -23.5655, "lng": -46.6205},
    "rj": {"nome": "Galpão do Coletivo Mãos na Central", "endereco": "Santo Cristo, Rio de Janeiro (fictício)", "lat": -22.8975, "lng": -43.2020},
    "for": {"nome": "Galpão do Coletivo Sol de Todos", "endereco": "Jacarecanga, Fortaleza (fictício)", "lat": -3.7230, "lng": -38.5420},
}

PONTOS: dict[str, list[dict]] = {
    "sp": [
        {
            "nome": "Praça da Sé", "bairro": "Sé", "lat": -23.5503, "lng": -46.6340,
            "pessoas": 25, "urgencia": 4, "relatos_30d": 12, "condicoes": ["frio"],
            "resumo": "Grupo grande na escadaria da catedral; noites frias sem cobertor suficiente.",
            "itens": _itens(("alimentacao", "marmita", 30), ("agasalho", "cobertor", 20), ("higiene", "kit de higiene", 10)),
        },
        {
            "nome": "Praça Princesa Isabel", "bairro": "Luz", "lat": -23.5345, "lng": -46.6390,
            "pessoas": 30, "urgencia": 5, "relatos_30d": 15, "condicoes": ["criancas", "feridos"],
            "resumo": "Maior concentração da região, com crianças. Pedido de curativos para feridos.",
            "itens": _itens(("alimentacao", "marmita", 40), ("agasalho", "cobertor", 25), ("saude", "kit de curativo", 10)),
        },
        {
            "nome": "Baixos do Viaduto Glicério", "bairro": "Glicério", "lat": -23.5560, "lng": -46.6270,
            "pessoas": 18, "urgencia": 3, "relatos_30d": 8, "condicoes": [],
            "resumo": "Ponto coberto, mas com goteiras. Falta comida à noite.",
            "itens": _itens(("agasalho", "cobertor", 15), ("alimentacao", "marmita", 20), ("saude", "kit de primeiros socorros", 4)),
        },
        {
            "nome": "Praça da República", "bairro": "República", "lat": -23.5431, "lng": -46.6425,
            "pessoas": 14, "urgencia": 3, "relatos_30d": 6, "condicoes": ["mulheres"],
            "resumo": "Muitas mulheres no grupo; pedido recorrente de absorventes e água.",
            "itens": _itens(("higiene", "absorvente", 40), ("agasalho", "casaco", 10), ("alimentacao", "garrafa de água", 30)),
        },
        {
            "nome": "Praça Marechal Deodoro", "bairro": "Santa Cecília", "lat": -23.5370, "lng": -46.6530,
            "pessoas": 12, "urgencia": 2, "relatos_30d": 4, "condicoes": [],
            "resumo": "Grupo menor embaixo do Minhocão, já atendido por uma ronda semanal.",
            "itens": _itens(("agasalho", "meia", 24), ("higiene", "kit de higiene", 12)),
        },
    ],
    "rj": [
        {
            "nome": "Central do Brasil", "bairro": "Centro", "lat": -22.9035, "lng": -43.1910,
            "pessoas": 28, "urgencia": 4, "relatos_30d": 14, "condicoes": ["chuva"],
            "resumo": "Maior grupo do centro; marquises não protegem da chuva com vento.",
            "itens": _itens(("alimentacao", "marmita", 35), ("agasalho", "cobertor", 15), ("higiene", "kit de higiene", 10)),
        },
        {
            "nome": "Arcos da Lapa", "bairro": "Lapa", "lat": -22.9131, "lng": -43.1800,
            "pessoas": 20, "urgencia": 3, "relatos_30d": 10, "condicoes": [],
            "resumo": "Grupo cresce nos fins de semana; falta água à tarde.",
            "itens": _itens(("alimentacao", "marmita", 25), ("alimentacao", "garrafa de água", 40), ("saude", "kit de curativo", 5)),
        },
        {
            "nome": "Cinelândia", "bairro": "Centro", "lat": -22.9105, "lng": -43.1755,
            "pessoas": 12, "urgencia": 3, "relatos_30d": 7, "condicoes": ["mulheres"],
            "resumo": "Várias mulheres no grupo; pedido de absorventes e água.",
            "itens": _itens(("higiene", "absorvente", 30), ("alimentacao", "garrafa de água", 24)),
        },
        {
            "nome": "Praça Mauá", "bairro": "Centro", "lat": -22.8968, "lng": -43.1812,
            "pessoas": 9, "urgencia": 2, "relatos_30d": 4, "condicoes": [],
            "resumo": "Grupo pequeno perto do museu, atendido por ronda semanal.",
            "itens": _itens(("alimentacao", "marmita", 10), ("agasalho", "meia", 18)),
        },
        {
            "nome": "Praça do Lido", "bairro": "Copacabana", "lat": -22.9650, "lng": -43.1765,
            "pessoas": 14, "urgencia": 4, "relatos_30d": 9, "condicoes": ["idosos"],
            "resumo": "Idosos no grupo, muito expostos ao sol da tarde.",
            "itens": _itens(("alimentacao", "garrafa de água", 30), ("saude", "kit de primeiros socorros", 4), ("alimentacao", "marmita", 14)),
        },
    ],
    "for": [
        {
            "nome": "Praça do Ferreira", "bairro": "Centro", "lat": -3.7275, "lng": -38.5260,
            "pessoas": 30, "urgencia": 4, "relatos_30d": 15, "condicoes": ["criancas"],
            "resumo": "Maior grupo do centro, com crianças; calor forte na hora do almoço.",
            "itens": _itens(("alimentacao", "garrafa de água", 60), ("alimentacao", "marmita", 30), ("higiene", "kit de higiene", 10)),
        },
        {
            "nome": "Praça José de Alencar", "bairro": "Centro", "lat": -3.7298, "lng": -38.5312,
            "pessoas": 18, "urgencia": 3, "relatos_30d": 9, "condicoes": [],
            "resumo": "Grupo ao lado do teatro; falta comida no fim do dia.",
            "itens": _itens(("alimentacao", "marmita", 20), ("alimentacao", "garrafa de água", 36), ("higiene", "kit de higiene", 15)),
        },
        {
            "nome": "Centro Dragão do Mar", "bairro": "Praia de Iracema", "lat": -3.7227, "lng": -38.5205,
            "pessoas": 12, "urgencia": 3, "relatos_30d": 6, "condicoes": [],
            "resumo": "Sem abrigo na quadra chuvosa; pedem lonas para cobrir.",
            "itens": _itens(("agasalho", "lona", 6), ("alimentacao", "marmita", 12)),
        },
        {
            "nome": "Mercado Central", "bairro": "Centro", "lat": -3.7262, "lng": -38.5232,
            "pessoas": 10, "urgencia": 2, "relatos_30d": 5, "condicoes": ["mulheres"],
            "resumo": "Mulheres no grupo; pedido de absorventes e água.",
            "itens": _itens(("higiene", "absorvente", 25), ("alimentacao", "garrafa de água", 20)),
        },
        {
            "nome": "Praça da Gentilândia", "bairro": "Benfica", "lat": -3.7420, "lng": -38.5385,
            "pessoas": 8, "urgencia": 2, "relatos_30d": 3, "condicoes": [],
            "resumo": "Grupo pequeno perto da universidade, atendido por estudantes.",
            "itens": _itens(("alimentacao", "marmita", 8), ("saude", "kit de curativo", 4)),
        },
    ],
}

DOADORES: dict[str, list[dict]] = {
    "sp": [
        {"nome": "Padaria Pão do Bixiga", "tipo": "padaria", "endereco": "Bela Vista (fictício)", "lat": -23.5580, "lng": -46.6450,
         "estoque": _itens(("alimentacao", "marmita", 25), ("alimentacao", "pão", 60))},
        {"nome": "Mercado Bom Preço Liberdade", "tipo": "mercado", "endereco": "Liberdade (fictício)", "lat": -23.5580, "lng": -46.6350,
         "estoque": _itens(("alimentacao", "garrafa de água", 60), ("alimentacao", "marmita", 20), ("higiene", "kit de higiene", 15))},
        {"nome": "Paróquia do Brás", "tipo": "igreja", "endereco": "Brás (fictício)", "lat": -23.5435, "lng": -46.6180,
         "estoque": _itens(("agasalho", "cobertor", 40), ("agasalho", "casaco", 15))},
        {"nome": "Condomínio Jardim Higienópolis", "tipo": "condominio", "endereco": "Higienópolis (fictício)", "lat": -23.5440, "lng": -46.6560,
         "estoque": _itens(("agasalho", "casaco", 20), ("agasalho", "meia", 40), ("higiene", "absorvente", 30))},
        {"nome": "Drogaria Santa Cecília", "tipo": "farmacia", "endereco": "Santa Cecília (fictício)", "lat": -23.5385, "lng": -46.6480,
         "estoque": _itens(("saude", "kit de primeiros socorros", 12), ("saude", "kit de curativo", 15), ("higiene", "absorvente", 40))},
        {"nome": "Cozinha Solidária Bom Retiro", "tipo": "cozinha", "endereco": "Bom Retiro (fictício)", "lat": -23.5270, "lng": -46.6400,
         "estoque": _itens(("alimentacao", "marmita", 60))},
    ],
    "rj": [
        {"nome": "Padaria Pão da Lapa", "tipo": "padaria", "endereco": "Lapa (fictício)", "lat": -22.9140, "lng": -43.1825,
         "estoque": _itens(("alimentacao", "marmita", 20), ("alimentacao", "pão", 50))},
        {"nome": "Supermercado Bom Preço Centro", "tipo": "mercado", "endereco": "Centro (fictício)", "lat": -22.9050, "lng": -43.1800,
         "estoque": _itens(("alimentacao", "garrafa de água", 80), ("higiene", "kit de higiene", 15))},
        {"nome": "Paróquia da Glória", "tipo": "igreja", "endereco": "Glória (fictício)", "lat": -22.9200, "lng": -43.1760,
         "estoque": _itens(("agasalho", "cobertor", 25), ("agasalho", "casaco", 10))},
        {"nome": "Condomínio Flamengo", "tipo": "condominio", "endereco": "Flamengo (fictício)", "lat": -22.9300, "lng": -43.1760,
         "estoque": _itens(("higiene", "absorvente", 40), ("agasalho", "meia", 30))},
        {"nome": "Farmácia Carioca", "tipo": "farmacia", "endereco": "Centro (fictício)", "lat": -22.9085, "lng": -43.1790,
         "estoque": _itens(("saude", "kit de curativo", 10), ("saude", "kit de primeiros socorros", 8))},
        {"nome": "Cozinha Solidária da Saúde", "tipo": "cozinha", "endereco": "Saúde (fictício)", "lat": -22.8990, "lng": -43.1870,
         "estoque": _itens(("alimentacao", "marmita", 50))},
    ],
    "for": [
        {"nome": "Panificadora Ferreira", "tipo": "padaria", "endereco": "Centro (fictício)", "lat": -3.7290, "lng": -38.5235,
         "estoque": _itens(("alimentacao", "marmita", 25), ("alimentacao", "pão", 60))},
        {"nome": "Mercadinho Beira-Mar", "tipo": "mercado", "endereco": "Meireles (fictício)", "lat": -3.7250, "lng": -38.5000,
         "estoque": _itens(("alimentacao", "garrafa de água", 120), ("higiene", "kit de higiene", 20))},
        {"nome": "Paróquia do Carmo", "tipo": "igreja", "endereco": "Centro (fictício)", "lat": -3.7305, "lng": -38.5247,
         "estoque": _itens(("agasalho", "lona", 10), ("agasalho", "cobertor", 10))},
        {"nome": "Condomínio Aldeota", "tipo": "condominio", "endereco": "Aldeota (fictício)", "lat": -3.7390, "lng": -38.5080,
         "estoque": _itens(("higiene", "absorvente", 40), ("alimentacao", "garrafa de água", 40))},
        {"nome": "Farmácia do Centro", "tipo": "farmacia", "endereco": "Centro (fictício)", "lat": -3.7280, "lng": -38.5290,
         "estoque": _itens(("saude", "kit de curativo", 12), ("saude", "kit de primeiros socorros", 6))},
        {"nome": "Cozinha Comunitária do Benfica", "tipo": "cozinha", "endereco": "Benfica (fictício)", "lat": -3.7410, "lng": -38.5360,
         "estoque": _itens(("alimentacao", "marmita", 60))},
    ],
}


def seed_ops(db: Session, cidade: str | None = None) -> None:
    """Apaga e recria os dados da central: de uma cidade, ou de todas se `cidade` for None."""
    cidades = [cidade] if cidade else list(CIDADES)
    for modelo in (RotaOtimizada, PontoDemanda, Doador, BaseOperacional):
        db.execute(delete(modelo).where(modelo.cidade_id.in_(cidades)))
    for c in cidades:
        db.add(BaseOperacional(cidade_id=c, **BASES[c]))
        db.add_all(PontoDemanda(cidade_id=c, **p) for p in PONTOS[c])
        db.add_all(Doador(cidade_id=c, **d) for d in DOADORES[c])
    db.commit()
