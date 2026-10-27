"""Texto livre → itens estruturados. Único ponto do sistema que usa LLM.

Fluxo: anonimiza → cache → regras locais se o texto for simples (cascata), senão LLM (ou o
fallback local) → valida o JSON → descarta itens sem evidência no texto → registra o uso.
O resultado é sempre uma PROPOSTA: quem publica é a ONG, depois de revisar.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, timedelta
from typing import Literal

from loguru import logger
from sqlalchemy.orm import Session

from app.catalogo import POR_SLUG, normalizar_slug
from app.config import settings
from app.llm import cache, prompts
from app.llm.client import LLMClient, Resultado, build_client
from app.llm.providers.offline import OfflineProvider
from app.llm.uso import origem_de, pode_chamar_llm, registrar_uso
from app.schemas import ExtracaoOut, ItemExtraido
from app.services import cascata, evidencia
from app.services.anonimizacao import anonimizar
from app.services.geocoding import normalizar
from app.services.parser_local import extrair_itens

Modo = Literal["demanda", "oferta"]

_DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
#: Quantidade assumida quando o texto não diz (a UI destaca o campo para revisão).
_QTD_PADRAO = {"demanda": 10, "oferta": 1}

_client: LLMClient | None = None


def _get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = build_client()
    return _client


def _parse_json(texto: str) -> list[dict]:
    limpo = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.MULTILINE).strip()
    dados = prompts.desescapar(json.loads(limpo))
    itens = dados.get("itens") if isinstance(dados, dict) else dados
    if not isinstance(itens, list):
        raise ValueError("JSON sem lista de itens")
    return [i for i in itens if isinstance(i, dict)]


def _normalizar_item(bruto: dict, modo: Modo, hoje: date) -> ItemExtraido | None:
    nome = str(bruto.get("item") or "").strip()[:120]
    if not nome:
        return None
    slug = normalizar_slug(str(bruto.get("categoria") or nome))
    try:
        quantidade = int(bruto.get("quantidade") or 0)
    except (TypeError, ValueError):
        quantidade = 0
    estimada = bool(bruto.get("quantidade_estimada")) or quantidade <= 0
    if estimada and quantidade <= 1:
        quantidade = _QTD_PADRAO[modo]
    try:
        urgencia = min(3, max(1, int(bruto.get("urgencia") or 2)))
    except (TypeError, ValueError):
        urgencia = 2
    prazo = None
    prazo_dias = bruto.get("prazo_dias")
    if modo == "demanda" and isinstance(prazo_dias, int | float) and 0 <= prazo_dias <= 60:
        prazo = hoje + timedelta(days=int(prazo_dias))
    return ItemExtraido(
        categoria=slug,
        categoria_nome=POR_SLUG[slug].nome,
        item=nome,
        quantidade=min(quantidade, 10_000),
        quantidade_estimada=estimada,
        urgencia=urgencia if modo == "demanda" else 2,
        prazo=prazo,
        evidencia=str(bruto.get("evidencia") or "").strip()[:160],
    )


def _aviso(origem: str, itens: list[ItemExtraido], descartados: int) -> str:
    partes = []
    if origem == "fallback":
        partes.append("Extração feita por regras locais (IA indisponível). Revise os itens.")
    if descartados:
        partes.append(f"Ignoramos {descartados} item(ns) que não aparecem na mensagem.")
    if not itens:
        partes.append("Não reconhecemos itens no texto. Tente algo como: '30 cobertores e 20 kits de higiene'.")
    return " ".join(partes)


def _chamar_llm(prompt: str, modo: Modo, metadata: dict) -> tuple[list[dict], Resultado]:
    resultado = _get_client().run(
        prompt,
        system=prompts.SYSTEM_EXTRACAO,
        schema=prompts.schema_itens(modo),
        metadata=metadata,
    )
    try:
        return _parse_json(resultado.completion.texto), resultado
    except (ValueError, json.JSONDecodeError) as exc:
        # JSON inválido do modelo: não arriscamos — o parser local assume.
        logger.warning("Saída do LLM inválida ({}); usando parser local.", exc)
        local = OfflineProvider()
        resultado = Resultado(
            local.generate(prompt, metadata=metadata), local.name, local.model, True, "JSON inválido"
        )
        return _parse_json(resultado.completion.texto), resultado


def extrair(db: Session, texto: str, modo: Modo, *, hoje: date | None = None) -> ExtracaoOut:
    """Cache → regras locais (se o texto for simples) → LLM. Tudo passa pela evidência."""
    hoje = hoje or date.today()
    feature = f"extrair_{modo}"
    texto_limpo, pii = anonimizar(texto)
    inicio = time.perf_counter()

    chave = cache.respostas.chave(feature, settings.modelo_efetivo, normalizar(texto_limpo), hoje.isoformat())
    if (guardado := cache.respostas.obter(chave)) is not None:
        registrar_uso(db, feature, None, "", 0, pii, origem="cache")
        return guardado.model_copy(update={"origem": "cache", "pii_removidos": pii, "offline": True})

    template = prompts.DEMANDA_TEMPLATE if modo == "demanda" else prompts.OFERTA_TEMPLATE
    prompt = template.format(
        texto=prompts.cercar(texto_limpo),
        hoje=hoje.isoformat(),
        dia_semana=_DIAS[hoje.weekday()],
        categorias=prompts.categorias_prompt(),
        regras=prompts.regras_prompt(),
    )
    resultado: Resultado | None = None
    if settings.cascata_enabled and cascata.decidir(texto_limpo).local:
        brutos, origem, fonte, modelo = extrair_itens(texto_limpo, hoje=hoje), "regras", "regras", "regras-locais"
    elif not pode_chamar_llm(db):
        # Teto diário atingido: regras locais, como se a IA estivesse fora do ar.
        brutos, origem, fonte, modelo = extrair_itens(texto_limpo, hoje=hoje), "fallback", "offline", "regras-locais"
    else:
        brutos, resultado = _chamar_llm(prompt, modo, {"feature": feature, "texto": texto_limpo})
        origem, fonte, modelo = origem_de(resultado), resultado.provider, resultado.model
    latencia_ms = int((time.perf_counter() - inicio) * 1000)

    # Anti-alucinação: item sem trecho correspondente na mensagem não chega à tela.
    brutos, descartados = evidencia.filtrar(texto_limpo, brutos)
    itens = [i for b in brutos if (i := _normalizar_item(b, modo, hoje)) is not None]
    registrar_uso(db, feature, resultado, prompt, latencia_ms, pii, origem=origem, descartados=descartados)
    saida = ExtracaoOut(
        itens=itens,
        fonte=fonte,
        modelo=modelo,
        offline=origem != "llm",
        origem=origem,  # type: ignore[arg-type]
        pii_removidos=pii,
        descartados=descartados,
        aviso=_aviso(origem, itens, descartados),
    )
    if origem in ("llm", "regras"):  # resposta de fallback (IA fora) não vale guardar
        cache.respostas.guardar(chave, saida)
    return saida

