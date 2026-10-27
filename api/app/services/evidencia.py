"""Anti-alucinação: todo item extraído precisa apontar o trecho do texto que o justifica.

O LLM devolve `evidencia` (trecho copiado da mensagem). Aqui conferimos se esse trecho
existe mesmo no texto; item sem evidência verificável é descartado antes de chegar à tela.
A comparação ignora acentos, maiúsculas e pontuação, e tolera singular/plural.
"""
from __future__ import annotations

import re

from loguru import logger

from app.services.geocoding import normalizar

_PALAVRA = re.compile(r"[a-z0-9]+")


def _mesma_palavra(palavra: str, tokens: set[str]) -> bool:
    if palavra in tokens:
        return True
    # "cobertor" × "cobertores", "pao" × "paes": compara o radical.
    radical = palavra[: max(3, len(palavra) - 2)]
    return any(t.startswith(radical) or palavra.startswith(t[: max(3, len(t) - 2)]) for t in tokens)


def tem_evidencia(texto: str, evidencia: str) -> bool:
    """True se o trecho aparece no texto (literal ou palavra por palavra)."""
    alvo = normalizar(texto)
    trecho = normalizar(evidencia).strip(" .,;:!?\"'“”()[]")
    if len(trecho) < 2 or not alvo:
        return False
    if trecho in alvo:
        return True
    palavras = [p for p in _PALAVRA.findall(trecho) if len(p) >= 3 and not p.isdigit()]
    if not palavras:
        return False
    tokens = set(_PALAVRA.findall(alvo))
    numeros = [p for p in _PALAVRA.findall(trecho) if p.isdigit()]
    return all(_mesma_palavra(p, tokens) for p in palavras) and all(n in tokens for n in numeros)


def _nome_valido(nome: str) -> bool:
    """O modelo às vezes corrompe a palavra (ex.: "água" virou "''"): exige ao menos 2 letras."""
    return len(re.findall(r"[a-z]", normalizar(nome))) >= 2


def filtrar(texto: str, itens: list[dict]) -> tuple[list[dict], int]:
    """Mantém só itens com nome legível e apoio no texto: a evidência OU o próprio nome.

    O nome conta porque o modelo às vezes corrompe só a cópia do trecho (ex.: "e %%%" no lugar
    de "e água"). Item que não é citado nem nomeado na mensagem continua descartado.
    """
    validos = []
    for i in itens:
        nome, trecho = str(i.get("item") or ""), str(i.get("evidencia") or "")
        if _nome_valido(nome) and (tem_evidencia(texto, trecho) or tem_evidencia(texto, nome)):
            validos.append(i)
        else:
            logger.warning("Item descartado sem evidência no texto: '{}' «{}»", nome, trecho)
    return validos, len(itens) - len(validos)
