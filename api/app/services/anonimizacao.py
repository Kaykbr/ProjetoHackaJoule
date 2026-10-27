"""Remove dados pessoais do texto ANTES de enviá-lo a qualquer LLM externo."""
from __future__ import annotations

import re

_PADROES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[cpf]"),
    (re.compile(r"(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?9?\d{4}[-\s]?\d{4}\b"), "[telefone]"),
)


def anonimizar(texto: str) -> tuple[str, int]:
    """Devolve o texto limpo e quantos dados pessoais foram removidos."""
    total = 0
    for padrao, marcador in _PADROES:
        texto, n = padrao.subn(marcador, texto)
        total += n
    return texto, total
