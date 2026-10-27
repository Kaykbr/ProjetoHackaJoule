"""Catálogo de categorias de doação.

É a fonte única de verdade para: categorias aceitas pelo LLM, sinônimos usados pelo
extrator offline e sensibilidade climática usada pelas regras de urgência.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Categoria:
    slug: str
    nome: str
    sinonimos: tuple[str, ...]
    sensivel_frio: bool = False
    sensivel_calor: bool = False


CATEGORIAS: tuple[Categoria, ...] = (
    Categoria(
        "agasalho", "Agasalhos",
        ("agasalho", "casaco", "jaqueta", "blusa de frio", "moletom", "blusão", "suéter",
         "gorro", "touca", "luva", "cachecol", "meia de lã"),
        sensivel_frio=True,
    ),
    Categoria(
        "cobertor", "Cobertores",
        ("cobertor", "coberta", "manta", "edredom", "edredon", "lençol", "saco de dormir",
         "colchonete"),
        sensivel_frio=True,
    ),
    Categoria(
        "higiene", "Higiene",
        ("higiene", "sabonete", "pasta de dente", "creme dental", "escova de dente",
         "absorvente", "papel higiênico", "desodorante", "shampoo", "xampu", "kit de higiene",
         "lenço umedecido", "fralda"),
    ),
    Categoria(
        "alimentacao", "Alimentação",
        ("alimento", "alimentação", "comida", "marmita", "quentinha", "lanche", "cesta básica",
         "arroz", "feijão", "macarrão", "pão", "biscoito", "leite", "fruta"),
    ),
    Categoria(
        "agua", "Água",
        ("água", "agua", "garrafa de água", "galão", "garrafinha"),
        sensivel_calor=True,
    ),
    Categoria(
        "calcado", "Calçados",
        ("calçado", "calcado", "sapato", "tênis", "tenis", "chinelo", "bota", "sandália"),
    ),
    Categoria(
        "roupa", "Roupas",
        ("roupa", "camiseta", "camisa", "calça", "bermuda", "short", "cueca", "calcinha",
         "meia", "vestido"),
    ),
    Categoria(
        "outros", "Outros",
        ("outro", "máscara", "mochila", "guarda-chuva", "capa de chuva", "ração"),
    ),
)

POR_SLUG: dict[str, Categoria] = {c.slug: c for c in CATEGORIAS}
SLUGS: tuple[str, ...] = tuple(POR_SLUG)


def normalizar_slug(valor: str | None) -> str:
    """Converte qualquer rótulo vindo do LLM/usuário para um slug válido do catálogo."""
    if not valor:
        return "outros"
    v = valor.strip().lower()
    if v in POR_SLUG:
        return v
    for cat in CATEGORIAS:
        if v == cat.nome.lower() or any(s in v for s in cat.sinonimos):
            return cat.slug
    return "outros"
