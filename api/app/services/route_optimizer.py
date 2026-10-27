"""Otimizador de última milha: quem doa o quê para quem, em que ordem, por quais ruas.

1. Prioriza os pontos (urgência relatada, ou risco em 24h no modo preditivo).
2. Match guloso: para cada item pedido, escolhe o estoque mais barato de buscar
   (distância até o ponto; doador já na rota sai mais barato; item igual vence substituto).
3. Sequência: base → coletas → entregas, cada fase por vizinho mais próximo + 2-opt.
4. OSRM traça a rota real nas ruas; sem ele, estimamos pela linha reta × fator de desvio.
5. CO2 evitado = viagens individuais de carro (ida e volta de cada doador a cada ponto)
   menos a rota única da van.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar

import httpx
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.cidades import CIDADE_PADRAO
from app.config import settings
from app.models import Doador, PontoDemanda, RotaOtimizada
from app.schemas.ops import ItemOps, ParadaOut, PendenciaOut, RotaIn, RotaOut
from app.services import central
from app.services.central import mesmo_item, substitui
from app.services.geo import distancia_km
from app.services.predictive_radar import calcular_radar

TEMPO_PARADA_MIN = 5.0

T = TypeVar("T")
LatLng = tuple[float, float]


# ------------------------------------------------------------------ sequência


def _custo_caminho(inicio: LatLng, ordem: list[T], coord: Callable[[T], LatLng]) -> float:
    total, atual = 0.0, inicio
    for x in ordem:
        c = coord(x)
        total += distancia_km(*atual, *c)
        atual = c
    return total


def ordenar(inicio: LatLng, itens: list[T], coord: Callable[[T], LatLng]) -> list[T]:
    """Vizinho mais próximo a partir de `inicio`, refinado com 2-opt (caminho aberto)."""
    restantes, ordem, atual = list(itens), [], inicio
    while restantes:
        prox = min(restantes, key=lambda x: distancia_km(*atual, *coord(x)))
        ordem.append(prox)
        restantes.remove(prox)
        atual = coord(prox)

    melhorou = True
    while melhorou and len(ordem) > 2:
        melhorou = False
        for i in range(len(ordem) - 1):
            for j in range(i + 2, len(ordem) + 1):
                nova = ordem[:i] + ordem[i:j][::-1] + ordem[j:]
                if _custo_caminho(inicio, nova, coord) + 1e-9 < _custo_caminho(inicio, ordem, coord):
                    ordem, melhorou = nova, True
    return ordem


# ------------------------------------------------------------------ match


def _alocar(alvos: list[tuple[PontoDemanda, list[ItemOps]]], doadores: list[Doador], max_entregas: int):
    """Distribui o estoque entre os pedidos, em ordem de prioridade.

    Para quando `max_entregas` pontos receberam algo. Ponto prioritário sem estoque não trava a
    rota: entra em `avaliados` (vira pendência) e o próximo da fila é tentado.
    Devolve coletas, entregas, baixas, pares doador→ponto, total pedido e pontos avaliados.
    """
    estoque = {d.id: {(i["categoria"], i["item"]): int(i["quantidade"]) for i in d.estoque or []} for d in doadores}
    por_id = {d.id: d for d in doadores}
    capacidade = settings.capacidade_veiculo_itens

    coletas: dict[int, dict[tuple[str, str], int]] = defaultdict(lambda: defaultdict(int))
    entregas: dict[int, dict[tuple[str, str], int]] = defaultdict(lambda: defaultdict(int))
    baixa_demanda: dict[int, dict[tuple[str, str], int]] = defaultdict(lambda: defaultdict(int))
    pares: set[tuple[int, int]] = set()
    pedido_total = 0
    avaliados: list[tuple[PontoDemanda, list[ItemOps]]] = []

    for ponto, necessidades in alvos:
        if len(entregas) >= max_entregas or capacidade <= 0:
            break
        avaliados.append((ponto, necessidades))
        for nec in necessidades:
            falta = nec.quantidade
            pedido_total += falta
            while falta > 0 and capacidade > 0:
                candidatos = [
                    (did, chave)
                    for did, itens in estoque.items()
                    for chave, q in itens.items()
                    if q > 0 and chave[0] == nec.categoria and substitui(nec.item, chave[1])
                ]
                if not candidatos:
                    break

                def custo(c: tuple[int, tuple[str, str]]) -> float:
                    d = por_id[c[0]]
                    km = distancia_km(d.lat, d.lng, ponto.lat, ponto.lng)
                    return km * (0.6 if c[0] in coletas else 1.0) * (1.0 if mesmo_item(c[1][1], nec.item) else 1.3)

                did, chave = min(candidatos, key=custo)
                q = min(falta, estoque[did][chave], capacidade)
                estoque[did][chave] -= q
                capacidade -= q
                falta -= q
                coletas[did][chave] += q
                entregas[ponto.id][chave] += q
                baixa_demanda[ponto.id][(nec.categoria, nec.item)] += q
                pares.add((did, ponto.id))
    return coletas, entregas, baixa_demanda, pares, pedido_total, avaliados


def _lista(itens: dict[tuple[str, str], int]) -> list[ItemOps]:
    return [ItemOps(categoria=c, item=i, quantidade=q) for (c, i), q in itens.items() if q > 0]  # type: ignore[arg-type]


# ------------------------------------------------------------------ OSRM


async def _rota_ruas(coords: list[LatLng]) -> tuple[list[float], list[float], list[LatLng], str]:
    """(km por trecho, minutos por trecho, geometria, fonte)."""
    if settings.osrm_enabled and len(coords) >= 2:
        caminho = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in coords)
        try:
            async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": settings.http_user_agent}) as c:
                r = await c.get(f"{settings.osrm_url}/{caminho}", params={"overview": "full", "geometries": "geojson"})
                r.raise_for_status()
                dados = r.json()
            rota = dados["routes"][0]
            km = [leg["distance"] / 1000 for leg in rota["legs"]]
            minutos = [leg["duration"] / 60 for leg in rota["legs"]]
            geometria = [(lat, lng) for lng, lat in rota["geometry"]["coordinates"]]
            return km, minutos, geometria, "osrm"
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            logger.warning("OSRM indisponível ({}); estimando pela linha reta.", exc)

    km = [distancia_km(*a, *b) * settings.fator_desvio_ruas for a, b in zip(coords, coords[1:], strict=False)]
    minutos = [d / settings.velocidade_media_kmh * 60 for d in km]
    return km, minutos, list(coords), "estimativa"


# ------------------------------------------------------------------ API do serviço


async def planejar(db: Session, entrada: RotaIn, cidade: str = CIDADE_PADRAO) -> RotaOut:
    base = central.base(db, cidade)
    pontos = central.pontos_abertos(db, cidade)
    doadores = [d for d in central.doadores(db, cidade) if d.estoque]

    if entrada.modo == "preditivo":
        radar = await calcular_radar(pontos, entrada.cenario, cidade)
        risco = {r.ponto_id: r for r in radar.riscos}
        ordem = sorted(pontos, key=lambda p: -risco[p.id].risco_24h)
        necessidades = {p.id: risco[p.id].demanda_projetada for p in pontos}
    else:
        ordem = sorted(pontos, key=lambda p: (-p.urgencia, -p.pessoas))
        necessidades = {p.id: central.itens_validos(p.itens) for p in pontos}

    alvos = [(p, necessidades[p.id]) for p in ordem if necessidades[p.id]]
    if not alvos:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nenhum ponto aberto com itens pedidos.")

    coletas, entregas, baixa_demanda, pares, pedido_total, alvos = _alocar(alvos, doadores, entrada.max_entregas)
    if not entregas:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Nenhum doador tem estoque dos itens pedidos agora. Vale uma campanha para esses itens.",
        )

    por_doador = {d.id: d for d in doadores}
    por_ponto = {p.id: p for p, _ in alvos}
    inicio: LatLng = (base.lat, base.lng)
    seq_coletas = ordenar(inicio, list(coletas), lambda did: (por_doador[did].lat, por_doador[did].lng))
    ultimo = (por_doador[seq_coletas[-1]].lat, por_doador[seq_coletas[-1]].lng)
    seq_entregas = ordenar(ultimo, list(entregas), lambda pid: (por_ponto[pid].lat, por_ponto[pid].lng))

    paradas_brutas = [("base", base.id, base.nome, base.lat, base.lng, [])]
    paradas_brutas += [("coleta", d, por_doador[d].nome, por_doador[d].lat, por_doador[d].lng, _lista(coletas[d])) for d in seq_coletas]
    paradas_brutas += [("entrega", p, por_ponto[p].nome, por_ponto[p].lat, por_ponto[p].lng, _lista(entregas[p])) for p in seq_entregas]
    # Volta à base: a comparação de CO2 com as viagens de ida e volta dos doadores fica justa.
    paradas_brutas.append(("retorno", base.id, f"Retorno: {base.nome}", base.lat, base.lng, []))

    km, minutos, geometria, fonte = await _rota_ruas([(lat, lng) for _, _, _, lat, lng, _ in paradas_brutas])
    paradas, relogio = [], 0.0
    for i, (tipo, ref, nome, lat, lng, itens) in enumerate(paradas_brutas):
        if i > 0:
            relogio += minutos[i - 1] + (TEMPO_PARADA_MIN if i > 1 else 0)
        paradas.append(ParadaOut(
            ordem=i, tipo=tipo, ref_id=ref, nome=nome, lat=lat, lng=lng, itens=itens,  # type: ignore[arg-type]
            distancia_desde_anterior_km=round(km[i - 1], 2) if i > 0 else 0.0,
            chegada_min=round(relogio, 1),
        ))

    distancia = sum(km)
    tempo = sum(minutos) + TEMPO_PARADA_MIN * (len(paradas) - 2)
    entregue = sum(q for itens in entregas.values() for q in itens.values())
    kg = sum(q * central.KG_POR_ITEM[c] for itens in entregas.values() for (c, _), q in itens.items())
    baseline_km = sum(
        2 * distancia_km(por_doador[d].lat, por_doador[d].lng, por_ponto[p].lat, por_ponto[p].lng) * settings.fator_desvio_ruas
        for d, p in pares
    )
    co2_rota = distancia * settings.fator_co2_van_kg_km
    co2_base = baseline_km * settings.fator_co2_carro_kg_km

    pendencias = []
    for p, nec in alvos:
        faltando = [
            ItemOps(categoria=n.categoria, item=n.item, quantidade=n.quantidade - baixa_demanda[p.id].get((n.categoria, n.item), 0))
            for n in nec
            if n.quantidade - baixa_demanda[p.id].get((n.categoria, n.item), 0) > 0
        ]
        if faltando:
            pendencias.append(PendenciaOut(ponto_id=p.id, nome=p.nome, itens=faltando))

    registro = RotaOtimizada(
        cidade_id=cidade, modo=entrada.modo, cenario=entrada.cenario, plano={}, distancia_km=round(distancia, 2),
        co2_evitado_kg=round(max(0.0, co2_base - co2_rota), 2), itens_entregues=entregue,
        kg_entregues=round(kg, 1), pessoas_atendidas=sum(por_ponto[p].pessoas for p in entregas),
    )
    db.add(registro)
    db.flush()
    db.refresh(registro)  # carrega o criada_em gerado pelo banco

    saida = RotaOut(
        id=registro.id, modo=entrada.modo, cenario=entrada.cenario, status="planejada", fonte_rota=fonte,  # type: ignore[arg-type]
        paradas=paradas, geometria=geometria, distancia_km=round(distancia, 2), tempo_min=round(tempo, 1),
        taxa_atendimento_pct=round(100 * entregue / pedido_total) if pedido_total else 0,
        itens_entregues=entregue, kg_entregues=round(kg, 1), pessoas_atendidas=registro.pessoas_atendidas,
        co2_rota_kg=round(co2_rota, 2), co2_baseline_kg=round(co2_base, 2), co2_evitado_kg=registro.co2_evitado_kg,
        viagens_evitadas=max(0, len(pares) - 1),
        nao_atendido=pendencias, criada_em=registro.criada_em,
    )
    registro.plano = {
        "saida": saida.model_dump(mode="json"),
        "baixa_estoque": {str(d): [i.model_dump() for i in _lista(itens)] for d, itens in coletas.items()},
        "baixa_demanda": {str(p): [i.model_dump() for i in _lista(itens)] for p, itens in baixa_demanda.items()},
    }
    db.commit()
    logger.info("Rota {} planejada: {} paradas, {:.1f} km, fonte {}", registro.id, len(paradas), distancia, fonte)
    return saida


def _descontar(itens: list[dict], baixas: list[dict]) -> list[dict]:
    restante = {(i["categoria"], i["item"]): int(i["quantidade"]) for i in itens}
    for b in baixas:
        chave = (b["categoria"], b["item"])
        if chave in restante:
            restante[chave] = max(0, restante[chave] - int(b["quantidade"]))
    return [{"categoria": c, "item": n, "quantidade": q} for (c, n), q in restante.items() if q > 0]


def rota_out(rota: RotaOtimizada) -> RotaOut:
    return RotaOut.model_validate({**rota.plano["saida"], "status": rota.status})


def concluir(db: Session, rota_id: int) -> RotaOut:
    """Registra a rota como feita: baixa os estoques e as demandas atendidas."""
    rota = db.get(RotaOtimizada, rota_id)
    if rota is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rota não encontrada.")
    if rota.status == "concluida":
        raise HTTPException(status.HTTP_409_CONFLICT, "Essa rota já foi concluída.")

    for did, baixas in rota.plano.get("baixa_estoque", {}).items():
        if doador := db.get(Doador, int(did)):
            doador.estoque = _descontar(doador.estoque or [], baixas)
    for pid, baixas in rota.plano.get("baixa_demanda", {}).items():
        if ponto := db.get(PontoDemanda, int(pid)):
            ponto.itens = _descontar(ponto.itens or [], baixas)
            if not ponto.itens:
                ponto.status = "atendido"
    rota.status = "concluida"
    db.commit()
    return rota_out(rota)
