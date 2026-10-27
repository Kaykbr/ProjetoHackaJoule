"""Avalia a leitura de mensagens contra os casos de casos_extracao.py e casos_relato.py.

Uso:
    python -m scripts.avaliar_extracao                  # suíte de itens, provider do .env
    python -m scripts.avaliar_extracao --suite relato   # agente de campo
    python -m scripts.avaliar_extracao --suite todas
    python -m scripts.avaliar_extracao --offline        # só regras locais (sem IA)
    python -m scripts.avaliar_extracao --sem-cascata    # toda mensagem vai ao LLM
    python -m scripts.avaliar_extracao -v               # mostra os itens extraídos

Grava num banco temporário: não mexe no doacerto.db.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

_DB = Path(tempfile.gettempdir()) / "doacerto_eval.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_DB.as_posix()}"
# Precisa valer antes de importar a configuração do app.
if "--sem-cascata" in sys.argv:
    os.environ["CASCATA_ENABLED"] = "false"

from loguru import logger  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.llm.client import LLMClient  # noqa: E402
from app.llm.providers.offline import OfflineProvider  # noqa: E402
from app.models import AiLog  # noqa: E402
from app.schemas import ExtracaoOut  # noqa: E402
from app.services import extracao, voice_agent  # noqa: E402
from app.services.geocoding import normalizar  # noqa: E402
from scripts.casos_extracao import CASOS, Caso, Qtd  # noqa: E402
from scripts.casos_relato import CASOS_RELATO, CasoRelato  # noqa: E402

HOJE = date(2026, 10, 23)
ROTULO_ORIGEM = {"llm": "IA", "regras": "REGRAS", "cache": "CACHE", "fallback": "LOCAL"}


def _qtd_ok(obtido: int, esperado: Qtd) -> bool:
    if esperado is None:
        return True
    if isinstance(esperado, tuple):
        return obtido in esperado
    return obtido == esperado


def _conferir_itens(totais: dict[str, int], n_itens: int, esperado: dict[str, Qtd],
                    proibido: tuple[str, ...], max_itens: int | None) -> list[str]:
    falhas = []
    for cat, qtd in esperado.items():
        if cat not in totais:
            falhas.append(f"faltou {cat}")
        elif not _qtd_ok(totais[cat], qtd):
            falhas.append(f"{cat}: {totais[cat]} (esperado {qtd})")
    falhas += [f"não devia ter {cat}" for cat in proibido if cat in totais]
    if max_itens is not None and n_itens > max_itens:
        falhas.append(f"{n_itens} itens (máx {max_itens})")
    return falhas


def avaliar(caso: Caso, r: ExtracaoOut) -> list[str]:
    totais: dict[str, int] = defaultdict(int)
    for item in r.itens:
        totais[item.categoria] += item.quantidade
    falhas = _conferir_itens(totais, len(r.itens), caso.esperado, caso.proibido, caso.max_itens)
    if caso.urgencia is not None and r.itens and max(i.urgencia for i in r.itens) != caso.urgencia:
        falhas.append(f"urgência {max(i.urgencia for i in r.itens)} (esperado {caso.urgencia})")
    if caso.prazo_dias is not None:
        prazos = {(i.prazo - HOJE).days for i in r.itens if i.prazo}
        if prazos != {caso.prazo_dias}:
            falhas.append(f"prazo {sorted(prazos) or 'nenhum'} (esperado {caso.prazo_dias})")
    return falhas


def avaliar_relato(caso: CasoRelato, leitura: voice_agent.Leitura) -> list[str]:
    r = leitura.relato
    totais: dict[str, int] = defaultdict(int)
    for item in r.itens:
        totais[item.categoria] += item.quantidade
    falhas = _conferir_itens(totais, len(r.itens), caso.esperado, caso.proibido, caso.max_itens)
    if caso.local and caso.local not in normalizar(f"{r.local_referencia} {r.bairro}"):
        falhas.append(f"local '{r.local_referencia}' (esperado ~'{caso.local}')")
    if caso.pessoas is not None and r.pessoas != caso.pessoas:
        falhas.append(f"pessoas {r.pessoas} (esperado {caso.pessoas})")
    minimo, maximo = caso.urgencia
    if not minimo <= r.urgencia <= maximo:
        falhas.append(f"urgência {r.urgencia} (esperado {minimo}-{maximo})")
    if faltando := set(caso.condicoes) - set(r.condicoes):
        falhas.append(f"faltou condição {sorted(faltando)}")
    return falhas


def _linha(ok: bool, origem: str, nome: str, falhas: list[str], descartados: int) -> str:
    extra = f"  [{descartados} sem evidência]" if descartados else ""
    detalhe = f"  → {'; '.join(falhas)}" if falhas else ""
    return f"{'OK  ' if ok else 'FALHA'} [{ROTULO_ORIGEM.get(origem, origem):6}] {nome}{extra}{detalhe}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["itens", "relato", "todas"], default="itens")
    parser.add_argument("--offline", action="store_true", help="só regras locais")
    parser.add_argument("--sem-cascata", action="store_true", help="toda mensagem vai ao LLM")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--caso", help="roda só os casos cujo nome contém este texto")
    parser.add_argument("--pausa", type=float, default=4.5, help="segundos após cada chamada ao LLM (15 req/min)")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    if _DB.exists():
        _DB.unlink()
    init_db()
    if args.offline:
        extracao._client = LLMClient(OfflineProvider(), offline=True)
        voice_agent._client = LLMClient(voice_agent.RelatoOfflineProvider(), offline=True)

    filtro = lambda nome: not args.caso or args.caso in nome  # noqa: E731
    placar: dict[str, tuple[int, int]] = {}
    with SessionLocal() as db:
        if args.suite in ("itens", "todas"):
            casos = [c for c in CASOS if filtro(c.nome)]
            ok = 0
            print("== itens (pedidos de ONG e ofertas de doadores)")
            for caso in casos:
                r = extracao.extrair(db, caso.texto, caso.modo, hoje=HOJE)  # type: ignore[arg-type]
                falhas = avaliar(caso, r)
                ok += not falhas
                print(_linha(not falhas, r.origem, caso.nome, falhas, r.descartados))
                if args.verbose or falhas:
                    for i in r.itens:
                        prazo = f" prazo+{(i.prazo - HOJE).days}d" if i.prazo else ""
                        est = "~" if i.quantidade_estimada else ""
                        print(f"         {i.categoria:12} {est}{i.quantidade:>4}  {i.item}  u{i.urgencia}{prazo}  «{i.evidencia}»")
                if r.origem == "llm":
                    time.sleep(args.pausa)
            placar["itens"] = (ok, len(casos))

        if args.suite in ("relato", "todas"):
            casos_r = [c for c in CASOS_RELATO if filtro(c.nome)]
            ok = 0
            print("== relatos de campo (agente de voz)")
            for caso in casos_r:
                leitura = voice_agent.ler_relato(db, caso.texto)
                falhas = avaliar_relato(caso, leitura)
                ok += not falhas
                print(_linha(not falhas, leitura.origem, caso.nome, falhas, leitura.descartados))
                if args.verbose or falhas:
                    r = leitura.relato
                    print(f"         local='{r.local_referencia}' pessoas={r.pessoas} urg={r.urgencia} cond={r.condicoes}")
                    for i in r.itens:
                        print(f"         {i.categoria:12} {i.quantidade:>4}  {i.item}  «{i.evidencia}»")
                if leitura.origem == "llm":
                    time.sleep(args.pausa)
            placar["relato"] = (ok, len(casos_r))

        logs = db.query(AiLog).all()

    origens = Counter(log.origem for log in logs)
    remotas = [log for log in logs if log.origem == "llm"]
    tokens = sum(log.tokens_entrada + log.tokens_saida for log in remotas)
    custo = sum(log.custo_estimado_usd for log in remotas)
    lat = sum(log.latencia_ms for log in remotas) / len(remotas) if remotas else 0
    print()
    for suite, (ok, total) in placar.items():
        print(f"{suite}: {ok}/{total} casos ok")
    print(
        f"origem: {origens.get('llm', 0)} IA · {origens.get('regras', 0)} regras (cascata) · "
        f"{origens.get('cache', 0)} cache · {origens.get('fallback', 0)} fallback · "
        f"{sum(log.descartados for log in logs)} itens sem evidência descartados"
    )
    if remotas:
        print(f"tokens: {tokens} ({tokens // len(remotas)}/chamada) · custo estimado: US$ {custo:.6f} · latência média: {lat:.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
