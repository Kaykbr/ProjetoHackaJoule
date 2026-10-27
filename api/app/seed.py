"""Dados de demonstração: São Paulo, Rio de Janeiro e Fortaleza.

Todas as ONGs são FICTÍCIAS. Os pontos são praças e largos públicos — nenhum dado
de pessoa em situação de rua é cadastrado.

Uso: `python -m app.seed` (apaga e recria o banco).
"""
from __future__ import annotations

from datetime import date, timedelta

from loguru import logger

from app.database import Base, SessionLocal, engine
from app.models import Demanda, Doacao, Ong, Ponto
from app.seed_ops import DOADORES, PONTOS, seed_ops

_SP = {"cidade_id": "sp", "cidade": "São Paulo"}
_RJ = {"cidade_id": "rj", "cidade": "Rio de Janeiro"}
_FOR = {"cidade_id": "for", "cidade": "Fortaleza"}

ONGS = [
    {
        **_SP,
        "nome": "Coletivo Abraço Centro",
        "descricao": "Rondas noturnas com sopa, cobertores e kits de higiene no centro.",
        "contato_publico": "@abracocentro (fictício)",
        "verificada": True,
        "pontos": [
            ("Praça da Sé", "Sé", -23.5503, -46.6340, "Próximo à escadaria da catedral", "entrega"),
            ("Praça da República", "República", -23.5431, -46.6425, "Lado da Av. Ipiranga", "entrega"),
            ("Praça Marechal Deodoro", "Santa Cecília", -23.5370, -46.6530, "Embaixo do Minhocão", "coleta"),
        ],
    },
    {
        **_SP,
        "nome": "Rede Calor Humano",
        "descricao": "Arrecada agasalhos e cobertores e distribui em pontos fixos.",
        "contato_publico": "rede.calorhumano@exemplo.org (fictício)",
        "verificada": True,
        "pontos": [
            ("Praça Princesa Isabel", "Luz", -23.5345, -46.6390, "Em frente à estação Luz", "entrega"),
            ("Largo da Concórdia", "Brás", -23.5420, -46.6170, "Saída da estação Brás", "coleta"),
            ("Baixos do Viaduto Glicério", "Glicério", -23.5560, -46.6270, "Sede da rede", "entrega"),
        ],
    },
    {
        **_SP,
        "nome": "Projeto Mesa Comum",
        "descricao": "Distribuição de marmitas e água; banho e barbearia solidária.",
        "contato_publico": "(fictício)",
        "verificada": False,
        "pontos": [
            ("Largo da Batata", "Pinheiros", -23.5668, -46.6930, "Saída da estação Faria Lima", "entrega"),
        ],
    },
    {
        **_RJ,
        "nome": "Coletivo Mãos na Central",
        "descricao": "Rondas com marmita e cobertor no centro do Rio.",
        "contato_publico": "@maosnacentral (fictício)",
        "verificada": True,
        "pontos": [
            ("Central do Brasil", "Centro", -22.9035, -43.1910, "Saída da Av. Presidente Vargas", "entrega"),
            ("Praça Tiradentes", "Centro", -22.9070, -43.1835, "Em frente ao teatro", "coleta"),
            ("Cinelândia", "Centro", -22.9105, -43.1755, "Escadaria da Câmara", "entrega"),
        ],
    },
    {
        **_RJ,
        "nome": "Rede Sopão da Lapa",
        "descricao": "Sopão às sextas e distribuição de água no verão.",
        "contato_publico": "(fictício)",
        "verificada": False,
        "pontos": [
            ("Arcos da Lapa", "Lapa", -22.9131, -43.1800, "Embaixo dos arcos", "entrega"),
            ("Praça do Lido", "Copacabana", -22.9650, -43.1765, "Lado da Av. Atlântica", "entrega"),
        ],
    },
    {
        **_FOR,
        "nome": "Coletivo Sol de Todos",
        "descricao": "Água, marmita e kit de higiene no centro de Fortaleza.",
        "contato_publico": "@soldetodos (fictício)",
        "verificada": True,
        "pontos": [
            ("Praça do Ferreira", "Centro", -3.7275, -38.5260, "Perto da Coluna da Hora", "entrega"),
            ("Praça José de Alencar", "Centro", -3.7298, -38.5312, "Lado do teatro", "coleta"),
            ("Mercado Central", "Centro", -3.7262, -38.5232, "Calçada da Av. Alberto Nepomuceno", "entrega"),
        ],
    },
    {
        **_FOR,
        "nome": "Rede Beira-Mar Solidária",
        "descricao": "Rondas noturnas na Praia de Iracema e no Benfica.",
        "contato_publico": "(fictício)",
        "verificada": False,
        "pontos": [
            ("Centro Dragão do Mar", "Praia de Iracema", -3.7227, -38.5205, "Em frente ao planetário", "entrega"),
            ("Praça da Gentilândia", "Benfica", -3.7420, -38.5385, "Ao lado da igreja", "entrega"),
        ],
    },
]

# (ponto, categoria, item, quantidade, recebida, urgência 1-3, prazo em dias ou None)
DEMANDAS = [
    ("Praça da Sé", "cobertor", "cobertor", 60, 12, 3, 2),
    ("Praça da Sé", "higiene", "kit de higiene", 80, 30, 2, None),
    ("Praça da Sé", "alimentacao", "marmita", 150, 90, 3, 0),
    ("Praça da República", "agasalho", "casaco", 40, 5, 2, 4),
    ("Praça da República", "calcado", "tênis", 25, 3, 1, None),
    ("Praça Marechal Deodoro", "cobertor", "manta", 30, 0, 2, None),
    ("Praça Marechal Deodoro", "higiene", "absorvente", 100, 20, 3, 3),
    ("Praça Princesa Isabel", "agasalho", "meia de lã", 120, 10, 2, None),
    ("Praça Princesa Isabel", "agua", "garrafa de água", 200, 60, 1, None),
    ("Largo da Concórdia", "roupa", "camiseta", 50, 35, 1, None),
    ("Largo da Concórdia", "cobertor", "cobertor", 45, 4, 2, 5),
    ("Baixos do Viaduto Glicério", "agasalho", "blusa de frio", 70, 20, 2, None),
    ("Baixos do Viaduto Glicério", "higiene", "escova de dente", 60, 58, 1, None),
    ("Largo da Batata", "alimentacao", "marmita", 120, 40, 2, 1),
    ("Largo da Batata", "agua", "garrafa de água", 150, 10, 2, None),
    # Rio de Janeiro
    ("Central do Brasil", "alimentacao", "marmita", 120, 40, 3, 0),
    ("Central do Brasil", "cobertor", "cobertor", 40, 5, 2, None),
    ("Praça Tiradentes", "higiene", "kit de higiene", 60, 20, 2, None),
    ("Cinelândia", "agua", "garrafa de água", 150, 30, 2, None),
    ("Arcos da Lapa", "alimentacao", "marmita", 90, 50, 2, 1),
    ("Arcos da Lapa", "roupa", "camiseta", 40, 10, 1, None),
    ("Praça do Lido", "agua", "garrafa de água", 80, 10, 3, None),
    ("Praça do Lido", "calcado", "chinelo", 30, 5, 1, None),
    # Fortaleza
    ("Praça do Ferreira", "agua", "garrafa de água", 250, 40, 3, 0),
    ("Praça do Ferreira", "alimentacao", "marmita", 100, 30, 2, None),
    ("Praça José de Alencar", "higiene", "kit de higiene", 70, 10, 2, None),
    ("Praça José de Alencar", "calcado", "chinelo", 40, 8, 1, None),
    ("Mercado Central", "alimentacao", "marmita", 80, 50, 2, 1),
    ("Centro Dragão do Mar", "agua", "garrafa de água", 120, 20, 2, None),
    ("Centro Dragão do Mar", "roupa", "camiseta", 50, 15, 1, None),
    ("Praça da Gentilândia", "higiene", "absorvente", 60, 10, 2, None),
]

# (ponto, item, quantidade, apelido) — doações já prometidas, aguardando entrega
DOACOES = [
    ("Praça da Sé", "cobertor", 6, "Marina"),
    ("Praça Princesa Isabel", "meia de lã", 20, "Grupo da academia"),
    ("Largo da Batata", "marmita", 15, "Anônimo"),
    ("Central do Brasil", "marmita", 10, "Igreja do bairro"),
    ("Arcos da Lapa", "camiseta", 5, "Ana"),
    ("Praça do Ferreira", "garrafa de água", 30, "Mercadinho do bairro"),
]


def run() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    hoje = date.today()

    with SessionLocal() as db:
        pontos: dict[str, Ponto] = {}
        for dados in ONGS:
            ong = Ong(
                cidade_id=dados["cidade_id"],
                cidade=dados["cidade"],
                nome=dados["nome"],
                descricao=dados["descricao"],
                contato_publico=dados["contato_publico"],
                verificada=dados["verificada"],
            )
            for nome, regiao, lat, lng, referencia, modo in dados["pontos"]:
                ponto = Ponto(
                    nome=nome, regiao=regiao, lat=lat, lng=lng,
                    referencia=referencia, modo_recebimento=modo,
                )
                ong.pontos.append(ponto)
                pontos[nome] = ponto
            db.add(ong)
        db.flush()

        demandas: dict[tuple[str, str], Demanda] = {}
        for ponto, categoria, item, qtd, recebida, urg, prazo in DEMANDAS:
            d = Demanda(
                ponto_id=pontos[ponto].id,
                categoria=categoria,
                item=item,
                quantidade=qtd,
                quantidade_recebida=recebida,
                urgencia_base=urg,
                prazo=hoje + timedelta(days=prazo) if prazo is not None else None,
                origem="manual",
            )
            db.add(d)
            demandas[(ponto, item)] = d
        db.flush()

        for ponto, item, qtd, apelido in DOACOES:
            d = demandas[(ponto, item)]
            d.quantidade_prometida += qtd
            db.add(Doacao(demanda_id=d.id, quantidade=qtd, doador_apelido=apelido))

        db.commit()
        seed_ops(db)
    logger.info(
        "Seed concluído: {} ONGs, {} pontos, {} demandas, {} doações | central: {} pontos, {} doadores.",
        len(ONGS), len(pontos), len(DEMANDAS), len(DOACOES),
        sum(map(len, PONTOS.values())), sum(map(len, DOADORES.values())),
    )


if __name__ == "__main__":
    run()
