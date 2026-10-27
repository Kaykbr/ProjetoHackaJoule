from __future__ import annotations

from datetime import date

from app.models import Demanda
from app.services.anonimizacao import anonimizar
from app.services.clima import Previsao
from app.services.parser_local import extrair_itens
from app.services.urgencia import calcular

SEXTA = date(2026, 10, 23)


def test_parser_local_extrai_quantidades_categorias_e_prazo() -> None:
    itens = extrair_itens(
        "Precisamos URGENTE de 40 cobertores, 20 kits de higiene e meias até segunda", hoje=SEXTA
    )
    por_categoria = {i["categoria"]: i for i in itens}

    assert por_categoria["cobertor"]["quantidade"] == 40
    assert por_categoria["higiene"]["quantidade"] == 20
    assert por_categoria["roupa"]["quantidade_estimada"] is True
    assert all(i["urgencia"] == 3 for i in itens)
    assert all(i["prazo_dias"] == 3 for i in itens)


def test_parser_local_prefere_sinonimo_mais_especifico() -> None:
    itens = extrair_itens("tenho duas blusas de frio e um par de tênis")
    assert {(i["categoria"], i["quantidade"]) for i in itens} == {("agasalho", 2), ("calcado", 1)}


def test_parser_local_ignora_texto_sem_itens() -> None:
    assert extrair_itens("olá, bom dia a todos") == []


def test_anonimizar_remove_telefone_email_e_cpf() -> None:
    texto, n = anonimizar("Falar com Ana (11) 98765-4321, ana@ong.org, CPF 123.456.789-09")
    assert n == 3
    assert "98765" not in texto and "ana@ong.org" not in texto and "123.456" not in texto


def _demanda(categoria: str, **kw) -> Demanda:
    base = dict(quantidade=100, quantidade_recebida=0, quantidade_prometida=0, urgencia_base=2, prazo=None)
    base.update(kw)
    return Demanda(categoria=categoria, item=categoria, **base)


def test_frio_aumenta_urgencia_so_de_itens_sensiveis() -> None:
    frio = Previsao(temp_min=6, temp_max=14, fonte="simulacao")
    agasalho_sem, agasalho_com = calcular(_demanda("agasalho"), None), calcular(_demanda("agasalho"), frio)
    higiene_sem, higiene_com = calcular(_demanda("higiene"), None), calcular(_demanda("higiene"), frio)

    assert agasalho_com.score == agasalho_sem.score + 25
    assert any("frio extremo" in r for r in agasalho_com.razoes)
    assert higiene_com.score == higiene_sem.score


def test_prazo_curto_e_baixa_cobertura_somam_razoes() -> None:
    u = calcular(_demanda("alimentacao", urgencia_base=3, prazo=SEXTA), None, hoje=SEXTA)
    assert u.score == 60 + 20 + 10
    assert u.nivel == "critica"
    assert len(u.razoes) == 3


def test_demanda_quase_coberta_perde_prioridade() -> None:
    u = calcular(_demanda("higiene", quantidade_recebida=80), None)
    assert u.score == 40 - 15
    assert u.nivel == "baixa"
