"""Cidades atendidas: centro do mapa, dicionário de lugares, clima plausível e exemplos.

Fonte única para tudo que muda de uma cidade para outra. Os lugares são praças, viadutos e
estações públicos onde ONGs costumam atuar, com os nomes como voluntários falam
(apelidos já normalizados: minúsculas, sem acento).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CidadeId = Literal["sp", "rj", "for"]
CIDADE_PADRAO: CidadeId = "sp"


@dataclass(frozen=True)
class Lugar:
    nome: str
    bairro: str
    lat: float
    lng: float
    apelidos: tuple[str, ...]


@dataclass(frozen=True)
class Cidade:
    id: CidadeId
    nome: str
    uf: str
    lat: float
    lng: float
    #: Caixa (oeste, norte, leste, sul) que limita o Nominatim à cidade.
    viewbox: str
    #: Mínima e máxima de um dia típico, usadas quando a Open-Meteo está fora do ar.
    temp_padrao: tuple[float, float]
    #: Cenários de simulação que fazem sentido no clima da cidade (id, rótulo).
    cenarios: tuple[tuple[str, str], ...]
    #: Relatos prontos para a demo (rótulo curto, texto).
    relatos_exemplo: tuple[tuple[str, str], ...]
    lugares: tuple[Lugar, ...]


SAO_PAULO = Cidade(
    id="sp", nome="São Paulo", uf="SP", lat=-23.5489, lng=-46.6388,
    viewbox="-46.83,-23.40,-46.36,-23.75", temp_padrao=(17.0, 25.0),
    cenarios=(("frente_fria", "Frente fria brusca"), ("tempestade", "Tempestade"), ("onda_de_calor", "Onda de calor")),
    relatos_exemplo=(
        ("Chuva no Anhangabaú", "Estamos no Vale do Anhangabaú, chovendo forte, 18 pessoas, duas crianças, precisamos urgente de 18 cobertores, 20 marmitas e 5 kits de higiene feminina"),
        ("Fome no Pacaembu", "Embaixo do viaduto Pacaembu tem 7 pessoas sem comer desde ontem, precisam de 7 marmitas e água"),
        ("Feridos na Sé", "Praça da Sé de novo, o frio apertou, chegaram mais 10 pessoas, precisamos de 10 cobertores e curativos para 2 feridos"),
        ("Idosa na Paulista", "Na Avenida Paulista perto do MASP, 9 pessoas, uma senhora idosa passando mal com febre, precisamos de remédio, 9 marmitas e 9 cobertores"),
    ),
    lugares=(
        Lugar("Praça da Sé", "Sé", -23.5503, -46.6340, ("praca da se", "catedral da se", "marco zero")),
        Lugar("Praça da República", "República", -23.5431, -46.6425, ("praca da republica", "republica")),
        Lugar("Praça Princesa Isabel", "Luz", -23.5345, -46.6390, ("praca princesa isabel", "princesa isabel")),
        Lugar("Estação da Luz", "Luz", -23.5352, -46.6347, ("estacao da luz", "parque da luz", "bairro da luz", "regiao da luz")),
        Lugar("Baixos do Viaduto Glicério", "Glicério", -23.5560, -46.6270, ("viaduto do glicerio", "viaduto glicerio", "glicerio")),
        Lugar("Praça Marechal Deodoro", "Santa Cecília", -23.5370, -46.6530, ("marechal deodoro", "minhocao", "elevado joao goulart", "santa cecilia")),
        Lugar("Largo do Arouche", "República", -23.5418, -46.6455, ("largo do arouche", "arouche")),
        Lugar("Vale do Anhangabaú", "Centro", -23.5450, -46.6365, ("vale do anhangabau", "anhangabau")),
        Lugar("Viaduto do Chá", "Centro", -23.5462, -46.6380, ("viaduto do cha",)),
        Lugar("Largo São Bento", "Centro", -23.5440, -46.6335, ("largo sao bento", "sao bento")),
        Lugar("Pátio do Colégio", "Sé", -23.5480, -46.6325, ("patio do colegio",)),
        Lugar("Parque Dom Pedro II", "Sé", -23.5470, -46.6280, ("parque dom pedro", "dom pedro")),
        Lugar("Rua 25 de Março", "Sé", -23.5425, -46.6305, ("25 de marco", "vinte e cinco de marco")),
        Lugar("Praça Roosevelt", "Consolação", -23.5487, -46.6460, ("praca roosevelt", "roosevelt")),
        Lugar("Largo da Concórdia", "Brás", -23.5420, -46.6170, ("largo da concordia", "bras")),
        Lugar("Praça da Liberdade", "Liberdade", -23.5555, -46.6355, ("praca da liberdade", "bairro da liberdade")),
        Lugar("Bela Vista", "Bela Vista", -23.5585, -46.6440, ("bela vista", "bixiga")),
        Lugar("Bom Retiro", "Bom Retiro", -23.5270, -46.6400, ("bom retiro",)),
        Lugar("Largo da Batata", "Pinheiros", -23.5668, -46.6930, ("largo da batata", "pinheiros")),
        Lugar("Avenida Paulista (MASP)", "Bela Vista", -23.5614, -46.6559, ("avenida paulista", "paulista", "masp")),
        Lugar("Praça Ramos de Azevedo", "República", -23.5452, -46.6390, ("ramos de azevedo", "theatro municipal", "teatro municipal")),
        Lugar("Terminal Parque Dom Pedro", "Sé", -23.5490, -46.6290, ("terminal parque dom pedro", "terminal dom pedro")),
        Lugar("Barra Funda", "Barra Funda", -23.5255, -46.6670, ("barra funda",)),
        Lugar("Mooca", "Mooca", -23.5600, -46.5990, ("mooca",)),
        Lugar("Cambuci", "Cambuci", -23.5660, -46.6200, ("cambuci",)),
    ),
)

RIO_DE_JANEIRO = Cidade(
    id="rj", nome="Rio de Janeiro", uf="RJ", lat=-22.9068, lng=-43.1790,
    viewbox="-43.80,-22.75,-43.10,-23.08", temp_padrao=(22.0, 30.0),
    cenarios=(("tempestade", "Temporal"), ("onda_de_calor", "Onda de calor")),
    relatos_exemplo=(
        ("Temporal na Central", "Estamos na Central do Brasil, chovendo muito, 20 pessoas, três crianças, precisamos urgente de 20 cobertores, 25 marmitas e 10 lonas"),
        ("Calor na Lapa", "Nos Arcos da Lapa, calor de 40 graus, 15 pessoas, precisamos de 40 garrafas de água e 15 marmitas"),
        ("Feridos na Cinelândia", "Cinelândia: 8 pessoas, dois feridos, precisamos de curativos e 8 marmitas"),
        ("Idoso em Copacabana", "Praça do Lido em Copacabana, 6 pessoas, um idoso passando mal, precisamos de remédio e 12 garrafas de água"),
    ),
    lugares=(
        Lugar("Central do Brasil", "Centro", -22.9035, -43.1910, ("central do brasil", "estacao central", "praca duque de caxias")),
        Lugar("Arcos da Lapa", "Lapa", -22.9131, -43.1800, ("arcos da lapa", "lapa")),
        Lugar("Cinelândia", "Centro", -22.9105, -43.1755, ("cinelandia", "praca floriano")),
        Lugar("Largo da Carioca", "Centro", -22.9070, -43.1775, ("largo da carioca",)),
        Lugar("Praça XV", "Centro", -22.9030, -43.1735, ("praca xv", "praca quinze", "praca 15")),
        Lugar("Praça Mauá", "Centro", -22.8968, -43.1812, ("praca maua", "maua")),
        Lugar("Praça Tiradentes", "Centro", -22.9070, -43.1835, ("praca tiradentes", "tiradentes")),
        Lugar("Campo de Santana", "Centro", -22.9065, -43.1885, ("campo de santana",)),
        Lugar("Aterro do Flamengo (Glória)", "Glória", -22.9210, -43.1735, ("aterro do flamengo", "aterro", "gloria")),
        Lugar("Praça do Lido", "Copacabana", -22.9650, -43.1765, ("praca do lido", "lido", "copacabana")),
        Lugar("Rodoviária Novo Rio", "Santo Cristo", -22.8990, -43.2095, ("rodoviaria novo rio", "novo rio", "rodoviaria")),
    ),
)

FORTALEZA = Cidade(
    id="for", nome="Fortaleza", uf="CE", lat=-3.7275, lng=-38.5260,
    viewbox="-38.64,-3.68,-38.40,-3.90", temp_padrao=(25.0, 31.0),
    cenarios=(("onda_de_calor", "Calor extremo"), ("tempestade", "Chuva forte (quadra chuvosa)")),
    relatos_exemplo=(
        ("Calor na Praça do Ferreira", "Praça do Ferreira, sol forte, 25 pessoas, precisamos urgente de 50 garrafas de água, 25 marmitas e protetor solar"),
        ("Chuva no Dragão do Mar", "Dragão do Mar, chuva forte desde a madrugada, 12 pessoas, precisamos de 12 lonas e 12 marmitas"),
        ("Crianças na José de Alencar", "Praça José de Alencar, 10 pessoas com duas crianças, precisamos de 10 kits de higiene e 20 marmitas"),
        ("Espanhol na Beira-Mar", "Estamos en la Beira-Mar, hay 7 personas, necesitamos agua y 7 almuerzos"),
    ),
    lugares=(
        Lugar("Praça do Ferreira", "Centro", -3.7275, -38.5260, ("praca do ferreira", "ferreira")),
        Lugar("Praça José de Alencar", "Centro", -3.7298, -38.5312, ("praca jose de alencar", "jose de alencar")),
        Lugar("Centro Dragão do Mar", "Praia de Iracema", -3.7227, -38.5205, ("dragao do mar", "praia de iracema")),
        Lugar("Mercado Central", "Centro", -3.7262, -38.5232, ("mercado central",)),
        Lugar("Beira-Mar (Feirinha)", "Meireles", -3.7254, -38.4955, ("beira mar", "beira-mar", "feirinha")),
        Lugar("Praça da Gentilândia", "Benfica", -3.7420, -38.5385, ("gentilandia", "benfica")),
        Lugar("Lagoa da Parangaba", "Parangaba", -3.7765, -38.5640, ("lagoa da parangaba", "parangaba")),
        Lugar("Praça do Carmo", "Centro", -3.7305, -38.5247, ("praca do carmo",)),
        Lugar("Catedral Metropolitana", "Centro", -3.7215, -38.5270, ("catedral de fortaleza", "catedral metropolitana", "catedral")),
        Lugar("Estação João Felipe", "Centro", -3.7240, -38.5310, ("estacao joao felipe", "joao felipe")),
    ),
)

CIDADES: dict[str, Cidade] = {c.id: c for c in (SAO_PAULO, RIO_DE_JANEIRO, FORTALEZA)}


def obter(cidade_id: str | None) -> Cidade:
    """Cidade pelo id; desconhecida ou vazia cai em São Paulo."""
    return CIDADES.get(cidade_id or CIDADE_PADRAO, SAO_PAULO)
