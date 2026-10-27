"""Extrator determinístico de itens a partir de texto livre (fallback sem IA).

Cobre o caso comum ("40 cobertores e 20 kits de higiene até sexta") com regex e o
catálogo de sinônimos. Não entende tudo que o LLM entende, mas garante que o app
continua funcionando sem internet ou sem chave de API.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from app.catalogo import CATEGORIAS

_NUMEROS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
    "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "duzia": 12,
    "quinze": 15, "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "cem": 100,
}
_DIAS_SEMANA = {
    "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6,
}
_URGENTE = ("urgente", "urgencia", "emergencia", "socorro", "hoje", "amanha", "agora")
#: Fim de frase só com espaço depois: "1.500" e "33.5" não quebram.
_SEPARADORES = re.compile(r",|;|\n|\+|[.!?:](?=\s)|\be\b|\btambem\b|\balem de\b")


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def _padrao(sinonimo: str) -> re.Pattern[str]:
    """Aceita plural em cada palavra: "kit de higiene" casa com "kits de higiene"."""
    palavras = (re.escape(p) + r"(?:e?s)?" for p in _normalizar(sinonimo).split())
    return re.compile(r"\b" + r"\s+".join(palavras))


#: (padrão, sinônimo original, categoria), do mais longo para o mais curto,
#: para "blusa de frio" ganhar de "blusa".
_SINONIMOS: list[tuple[re.Pattern[str], str, str]] = sorted(
    ((_padrao(s), s, cat.slug) for cat in CATEGORIAS for s in cat.sinonimos),
    key=lambda t: len(t[1]),
    reverse=True,
)


def _quantidade(segmento: str) -> int | None:
    digitos = re.search(r"\b(\d{1,4})\b", segmento)
    if digitos:
        return int(digitos.group(1))
    for palavra, valor in _NUMEROS.items():
        if re.search(rf"\b{palavra}\b", segmento):
            return valor
    return None


def _prazo_dias(texto: str, hoje: date) -> int | None:
    if "hoje" in texto:
        return 0
    if "amanha" in texto:
        return 1
    for nome, indice in _DIAS_SEMANA.items():
        if re.search(rf"\b{nome}\b", texto):
            return (indice - hoje.weekday()) % 7 or 7
    if "semana" in texto:
        return 6 - hoje.weekday() or 7
    return None


def segmentos(texto: str) -> list[tuple[str, str]]:
    """(trecho normalizado, trecho original) entre separadores ("," ";" " e "…).

    A normalização preserva o tamanho do texto em português (só tira acentos e caixa), então
    as mesmas posições recortam o original, que vira a evidência mostrada ao usuário.
    """
    normal = _normalizar(texto)
    mesmo_tamanho = len(normal) == len(texto)
    pedacos, inicio = [], 0
    for sep in [*_SEPARADORES.finditer(normal), None]:
        fim = sep.start() if sep else len(normal)
        trecho = normal[inicio:fim].strip()
        if trecho:
            original = texto[inicio:fim].strip() if mesmo_tamanho else trecho
            pedacos.append((trecho, original))
        inicio = sep.end() if sep else fim
    return pedacos


def extrair_itens(texto: str, *, hoje: date | None = None) -> list[dict]:
    """Lista de itens no mesmo formato que pedimos ao LLM (inclusive `evidencia`)."""
    hoje = hoje or date.today()
    normal = _normalizar(texto)
    urgencia = 3 if any(p in normal for p in _URGENTE) else 2
    prazo = _prazo_dias(normal, hoje)

    itens: dict[tuple[str, str], dict] = {}
    for segmento, original in segmentos(texto):
        achado = next(
            ((orig, slug) for padrao, orig, slug in _SINONIMOS if padrao.search(segmento)),
            None,
        )
        if achado is None:
            continue
        nome, slug = achado
        quantidade = _quantidade(segmento)
        chave = (slug, nome)
        if chave in itens:
            itens[chave]["quantidade"] += quantidade or 1
            continue
        itens[chave] = {
            "categoria": slug,
            "item": nome,
            "quantidade": quantidade or 1,
            "quantidade_estimada": quantidade is None,
            "urgencia": urgencia,
            "prazo_dias": prazo,
            "evidencia": original.strip(" .!?:")[:120],
        }
    return list(itens.values())
