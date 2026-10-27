"""Cascata: as regras locais resolvem a mensagem simples; o LLM fica para a ambígua.

A decisão é conservadora de propósito: só fica local o texto em que TODA palavra está
explicada (um número seguido de um item do catálogo, ou palavras de preenchimento como
"precisamos" e "por favor") e sem nenhum marcador de ambiguidade. Na dúvida, vai ao LLM.
Os marcadores foram ajustados com `python -m scripts.avaliar_extracao --suite todas`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.geocoding import normalizar
from app.services.parser_local import _SINONIMOS, segmentos

_MAX_CARACTERES = 220

#: Sinais de que o texto precisa de interpretação: negação, itens já recebidos, dinheiro,
#: unidades de embalagem, conteúdo de kit, tamanho/numeração, outra língua, ordens ao sistema.
_AMBIGUO = re.compile(
    r"\bnao\b|\bnem\b|\bsem\b|ja receb|ja cheg|sobr|\bpix\b|dinheiro|volunt|duzia|fardo|pacote|"
    r"caixa|\bkg\b|\bkilo|litro|\(|tamanho|\bn[o°º]\s*\d|\bnumero\b|ignore|sistema|instruc|"
    r"\bnecesit|\bhay\b|\bpersonas?\b|frazad|comida para todos|cerca de|\bmais ou menos\b"
)
#: No relato, avaliar urgência com vulneráveis ou feridos é trabalho para o LLM.
_AMBIGUO_RELATO = re.compile(r"crianc|bebe|idos[oa]|ferid|gestant|gravid|doente|febre|passando mal|sangr")

_NUMERO = re.compile(r"\b\d{1,4}\b")
_PALAVRA = re.compile(r"[a-z]+")

#: Palavras que não carregam pedido (já normalizadas: sem acento, minúsculas).
_PREENCHIMENTO = frozenset("""
a o as os um uma uns umas de da do das dos e no na nos nas em com para pra por que se ja ate
precisamos preciso precisa precisam precisando necessitamos necessita pedimos pedindo estamos esta
estao tem temos tenho posso podemos quero queremos doar doacao doacoes ajudar ajuda ajude quem
puder pode favor urgente urgencia urgentemente hoje amanha agora noite dia tarde manha ronda
pessoal gente galera bom boa oi ola obrigado obrigada aqui ali mais muito muita ponto local
entregar levar trazer semana sabado domingo segunda terca quarta quinta sexta falta faltam
faltando novo nova novos novas usado usados usadas limpo limpos bom estado tambem
""".split())

#: Vocabulário extra que o relato de campo pode usar sem precisar de interpretação.
_PREENCHIMENTO_RELATO = frozenset("""
pessoas pessoa moradores morador chuva chovendo forte frio gelado gelada vento ventando situacao
rua estamos aqui
""".split())


@dataclass
class Decisao:
    local: bool
    motivos: list[str] = field(default_factory=list)


def _item_em(segmento: str) -> re.Match[str] | None:
    for padrao, _, _ in _SINONIMOS:
        if m := padrao.search(segmento):
            return m
    return None


def decidir(texto: str, *, relato: bool = False, explicadas: frozenset[str] = frozenset()) -> Decisao:
    """Decide se as regras locais bastam para esta mensagem (já anonimizada)."""
    normal = normalizar(texto)
    motivos: list[str] = []
    if len(normal) > _MAX_CARACTERES:
        motivos.append("texto longo")
    if m := _AMBIGUO.search(normal):
        motivos.append(f"ambiguidade: '{m.group(0).strip()}'")
    if relato and (m := _AMBIGUO_RELATO.search(normal)):
        motivos.append(f"avaliação de risco: '{m.group(0)}'")

    preenchimento = _PREENCHIMENTO | explicadas | (_PREENCHIMENTO_RELATO if relato else frozenset())
    tem_item = False
    for segmento, _ in segmentos(texto):
        if relato:
            # "18 pessoas" é contagem de gente, não pedido de item.
            segmento = re.sub(r"\b\d{1,4}\s*(?:pessoas?|moradores?)\b", " pessoas ", segmento)
        numeros = list(_NUMERO.finditer(segmento))
        item = _item_em(segmento)
        if item:
            tem_item = True
            if len(numeros) != 1:
                motivos.append(f"quantidade incerta em '{segmento}'")
            elif numeros[0].start() > item.start():
                motivos.append(f"número depois do item em '{segmento}'")
            continue
        if numeros:
            motivos.append(f"número sem item conhecido em '{segmento}'")
        sobras = [p for p in _PALAVRA.findall(segmento) if p not in preenchimento]
        if sobras:
            motivos.append(f"palavras não reconhecidas: {', '.join(sobras[:4])}")
    if not tem_item:
        motivos.append("nenhum item reconhecido")
    return Decisao(local=not motivos, motivos=motivos)
