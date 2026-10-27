"use client";

import { ArrowLeft, Eye, HeartHandshake, Leaf, PackageCheck, RotateCcw, TrendingUp, Users, X, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { COR_NIVEL, COR_OPS, ROTULO_NIVEL } from "@/components/ops/cores";
import type { Selecao, Visao } from "@/components/ops/mapa-ops";
import { MapaOpsDinamico } from "@/components/ops/mapa-ops-dinamico";
import { PainelRadar } from "@/components/ops/painel-radar";
import { PainelRota } from "@/components/ops/painel-rota";
import { PainelVoz } from "@/components/ops/painel-voz";
import { Etiqueta, ListaItens, Urgencia } from "@/components/ops/ui-ops";
import { SeletorCidade } from "@/components/seletor-cidade";
import { Logo } from "@/components/ui/logo";
import { useToast } from "@/components/ui/toast";
import { ops } from "@/lib/api";
import { useCidade } from "@/lib/cidade";
import type { Cenario, EstadoOps, KpisOps, ModoRota, Radar, RelatoResultado, RotaOtimizada } from "@/lib/types-ops";

const ATUALIZAR_A_CADA_MS = 10_000;

/** Número que conta até o valor novo (dá vida aos KPIs quando uma rota é concluída). */
function useContagem(alvo: number): number {
  const [valor, setValor] = useState(alvo);
  const anterior = useRef(alvo);
  useEffect(() => {
    const de = anterior.current;
    anterior.current = alvo;
    if (de === alvo) return;
    const inicio = performance.now();
    let quadro = 0;
    const passo = (agora: number) => {
      const t = Math.min(1, (agora - inicio) / 900);
      setValor(de + (alvo - de) * (1 - (1 - t) ** 3));
      if (t < 1) quadro = requestAnimationFrame(passo);
    };
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, [alvo]);
  return valor;
}

function Kpi({ icone: Icone, rotulo, valor, sufixo = "", casas = 0 }: { icone: LucideIcon; rotulo: string; valor: number; sufixo?: string; casas?: number }) {
  const animado = useContagem(valor);
  return (
    <div className="flex min-w-[150px] items-center gap-2.5 rounded-lg border border-ops-linha bg-ops-painel px-3 py-2">
      <Icone className="h-4 w-4 shrink-0 text-ops-ciano" aria-hidden />
      <div>
        <p className="font-display text-lg font-semibold leading-none tabular-nums text-ops-texto">
          {animado.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas })}
          {sufixo}
        </p>
        <p className="mt-0.5 text-[11px] text-ops-muted">{rotulo}</p>
      </div>
    </div>
  );
}

function Topo({ kpis, onReset }: { kpis: KpisOps | null; onReset: (() => void) | null }) {
  const { cidade } = useCidade();
  return (
    <header className="flex flex-col gap-3 border-b border-ops-linha bg-ops-bg px-4 py-3 lg:h-[72px] lg:flex-row lg:items-center lg:py-0">
      <div className="flex items-center gap-3">
        <Link href="/" aria-label="Voltar ao site" className="text-ops-muted hover:text-ops-texto">
          <ArrowLeft className="h-4 w-4" aria-hidden />
        </Link>
        <Logo className="h-8 w-8" />
        <div>
          <p className="font-display text-base font-semibold leading-tight text-ops-texto">Central de operações</p>
          <p className="flex items-center gap-1.5 text-[11px] text-ops-muted">
            <span className="h-1.5 w-1.5 animate-pulsar rounded-full bg-ops-verde" aria-hidden />
            Ao vivo, {cidade.nome}
          </p>
        </div>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 lg:ml-auto lg:pb-0 [scrollbar-width:none]">
        <Kpi icone={Users} rotulo="Pessoas assistidas" valor={kpis?.pessoas_assistidas ?? 0} />
        <Kpi icone={HeartHandshake} rotulo="Match de doações" valor={kpis?.match_doacoes_pct ?? 0} sufixo="%" />
        <Kpi icone={PackageCheck} rotulo="Desperdício evitado" valor={kpis?.kg_desperdicio_evitado ?? 0} sufixo=" kg" casas={1} />
        <Kpi icone={Leaf} rotulo="CO₂ economizado" valor={kpis?.co2_economizado_kg ?? 0} sufixo=" kg" casas={1} />
      </div>
      <div className="flex items-center gap-2 self-start lg:self-auto">
        <SeletorCidade tema="escuro" />
        {onReset && (
          <button
            onClick={onReset}
            title="Voltar aos dados de demonstração"
            className="inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-ops-muted hover:bg-ops-elevado hover:text-ops-texto"
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden />
            Reiniciar demo
          </button>
        )}
      </div>
    </header>
  );
}

export default function OperacaoPage() {
  const toast = useToast();
  const [estado, setEstado] = useState<EstadoOps | null>(null);
  // No site público, só quem abriu com `?admin=<ADMIN_TOKEN>` vê "Reiniciar demo".
  const [tokenAdmin, setTokenAdmin] = useState("");
  const podeReiniciar = Boolean(tokenAdmin) || process.env.NODE_ENV !== "production";
  useEffect(() => {
    try {
      const doLink = new URLSearchParams(window.location.search).get("admin");
      if (doLink) sessionStorage.setItem("doacerto-admin", doLink);
      setTokenAdmin(doLink ?? sessionStorage.getItem("doacerto-admin") ?? "");
    } catch {
      /* sessionStorage bloqueado: sem botão de reset */
    }
  }, []);
  const [radar, setRadar] = useState<Radar | null>(null);
  const [carregandoRadar, setCarregandoRadar] = useState(false);
  const [cenario, setCenario] = useState<Cenario>("normal");
  const [visao, setVisao] = useState<Visao>("atual");
  const [rota, setRota] = useState<RotaOtimizada | null>(null);
  const [rotaDesatualizada, setRotaDesatualizada] = useState(false);
  // aoRelato roda depois de um await: lê a rota atual pelo ref, não pelo valor capturado.
  const rotaRef = useRef(rota);
  rotaRef.current = rota;
  const [modoRota, setModoRota] = useState<ModoRota>("atual");
  const [maxEntregas, setMaxEntregas] = useState(4);
  const [gerando, setGerando] = useState(false);
  const [concluindo, setConcluindo] = useState(false);
  const [novos, setNovos] = useState<Set<number>>(new Set());
  const [selecao, setSelecao] = useState<Selecao>(null);

  const carregarEstado = useCallback(async () => {
    try {
      setEstado(await ops.estado());
    } catch (e) {
      toast({ tipo: "erro", titulo: "Central fora do ar", descricao: (e as Error).message });
    }
  }, [toast]);

  useEffect(() => {
    void carregarEstado();
    // "Tempo real" simples: outros voluntários também registram relatos.
    const id = window.setInterval(() => document.visibilityState === "visible" && void carregarEstado(), ATUALIZAR_A_CADA_MS);
    return () => window.clearInterval(id);
  }, [carregarEstado]);

  // O risco depende dos pontos: recalcula quando um ponto entra, muda ou sai.
  const assinatura = estado?.demandas.map((d) => `${d.id}:${d.atualizado_em}:${d.total_itens}`).join("|") ?? "";
  useEffect(() => {
    if (!estado) return;
    let ativo = true;
    setCarregandoRadar(true);
    ops
      .radar(cenario)
      .then((r) => ativo && setRadar(r))
      .catch((e: Error) => toast({ tipo: "erro", titulo: "Radar indisponível", descricao: e.message }))
      .finally(() => ativo && setCarregandoRadar(false));
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cenario, assinatura]);

  const riscos = useMemo(() => new Map(radar?.riscos.map((r) => [r.ponto_id, r]) ?? []), [radar]);

  async function moverPonto(id: number, lat: number, lng: number) {
    try {
      const ponto = await ops.moverPonto(id, lat, lng);
      setEstado((e) => (e ? { ...e, demandas: e.demandas.map((d) => (d.id === id ? ponto : d)) } : e));
      if (rota?.status === "planejada") setRotaDesatualizada(true);
      toast({ tipo: "sucesso", titulo: "Local corrigido", descricao: `${ponto.nome} foi movido no mapa.` });
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não deu para mover o ponto", descricao: (e as Error).message });
    }
  }

  function aoRelato(r: RelatoResultado) {
    setEstado((e) =>
      e ? { ...e, demandas: [...e.demandas.filter((d) => d.id !== r.ponto.id), r.ponto] } : e,
    );
    setNovos((s) => new Set(s).add(r.ponto.id));
    window.setTimeout(() => setNovos((s) => {
      const n = new Set(s);
      n.delete(r.ponto.id);
      return n;
    }), 12_000);
    setSelecao({ tipo: "demanda", id: r.ponto.id });
    // A rota continua na tela: apagá-la fazia a rota recém-gerada sumir quando um relato
    // (mais lento, passa pela IA) chegava logo depois. Só avisamos que ela não inclui o relato.
    setRotaDesatualizada((atual) => atual || rotaRef.current?.status === "planejada");
    void carregarEstado();
  }

  function aoCenario(c: Cenario) {
    setCenario(c);
    const previsao = c !== "normal";
    setVisao(previsao ? "preditiva" : "atual");
    setModoRota(previsao ? "preditivo" : "atual");
  }

  async function gerarRota() {
    setGerando(true);
    try {
      const r = await ops.gerarRota(modoRota, cenario, maxEntregas);
      setRota(r);
      setRotaDesatualizada(false);
      setSelecao(null);
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não deu para gerar a rota", descricao: (e as Error).message });
    } finally {
      setGerando(false);
    }
  }

  async function concluirRota() {
    if (!rota) return;
    setConcluindo(true);
    try {
      const r = await ops.concluirRota(rota.id);
      setRota(r);
      await carregarEstado();
      toast({
        tipo: "sucesso",
        titulo: `${r.itens_entregues} itens entregues para ${r.pessoas_atendidas} pessoas`,
        descricao: `${r.co2_evitado_kg.toLocaleString("pt-BR")} kg de CO₂ evitados. Estoques e pedidos atualizados.`,
      });
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não deu para concluir", descricao: (e as Error).message });
    } finally {
      setConcluindo(false);
    }
  }

  async function reiniciar() {
    try {
      setEstado(await ops.reset(tokenAdmin));
      setRota(null);
      setRotaDesatualizada(false);
      setSelecao(null);
      aoCenario("normal");
      toast({ tipo: "info", titulo: "Demo reiniciada", descricao: "Pontos, doadores e KPIs voltaram ao início." });
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não deu para reiniciar", descricao: (e as Error).message });
    }
  }

  const demandaSel = selecao?.tipo === "demanda" ? estado?.demandas.find((d) => d.id === selecao.id) : undefined;
  const doadorSel = selecao?.tipo === "doador" ? estado?.doadores.find((d) => d.id === selecao.id) : undefined;
  const riscoSel = demandaSel ? riscos.get(demandaSel.id) : undefined;

  return (
    // -mb-16: anula o espaço da navegação inferior do layout raiz (aqui ela não aparece).
    <div className="-mb-16 flex min-h-dvh flex-col bg-ops-bg text-ops-texto md:mb-0 lg:h-dvh lg:overflow-hidden">
      <Topo kpis={estado?.kpis ?? null} onReset={podeReiniciar ? reiniciar : null} />

      <div className="flex flex-1 flex-col lg:grid lg:min-h-0 lg:grid-cols-[340px_minmax(0,1fr)_370px]">
        {/* ------------------------------------------------------------ mapa */}
        <section className="relative h-[55vh] border-b border-ops-linha lg:order-2 lg:h-auto lg:border-b-0" aria-label="Mapa operacional">
          {estado ? (
            <MapaOpsDinamico
              base={estado.base}
              demandas={estado.demandas}
              doadores={estado.doadores}
              visao={visao}
              riscos={riscos}
              rota={rota}
              novos={novos}
              selecao={selecao}
              onSelecionar={setSelecao}
              onMover={(id, lat, lng) => void moverPonto(id, lat, lng)}
            />
          ) : (
            <div className="h-full w-full animate-pulse bg-ops-painel" />
          )}

          <div className="absolute left-1/2 top-3 z-[400] -translate-x-1/2">
            <div className="inline-flex rounded-lg border border-ops-linha bg-ops-painel p-1 shadow-float" role="radiogroup" aria-label="Visão do mapa">
              {(
                [
                  ["atual", "Visão atual", Eye],
                  ["preditiva", "Previsão +24h", TrendingUp],
                ] as [Visao, string, LucideIcon][]
              ).map(([valor, rotulo, Icone]) => (
                <button
                  key={valor}
                  role="radio"
                  aria-checked={visao === valor}
                  onClick={() => setVisao(valor)}
                  className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                    visao === valor ? "bg-ops-ciano text-ops-bg" : "text-ops-muted hover:text-ops-texto"
                  }`}
                >
                  <Icone className="h-3.5 w-3.5" aria-hidden />
                  {rotulo}
                </button>
              ))}
            </div>
          </div>

          <div className="absolute bottom-3 left-3 z-[400] max-w-[340px]">
            {demandaSel || doadorSel ? (
              <article className="animate-fade-up rounded-lg border border-ops-linha bg-ops-painel p-3 shadow-float">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: demandaSel ? COR_OPS.vermelho : COR_OPS.verde }}>
                      {demandaSel ? "Ponto de demanda" : "Doador"}
                    </p>
                    <p className="truncate font-semibold">{demandaSel?.nome ?? doadorSel?.nome}</p>
                    <p className="text-xs text-ops-muted">{demandaSel ? demandaSel.bairro : `${doadorSel?.tipo}, ${doadorSel?.endereco}`}</p>
                  </div>
                  <button onClick={() => setSelecao(null)} className="text-ops-muted hover:text-ops-texto" aria-label="Fechar detalhes">
                    <X className="h-4 w-4" aria-hidden />
                  </button>
                </div>
                {demandaSel && (
                  <>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Urgencia valor={demandaSel.urgencia} />
                      <Etiqueta>{demandaSel.pessoas} pessoas</Etiqueta>
                      <Etiqueta>{demandaSel.relatos_30d} relatos em 30 dias</Etiqueta>
                      {riscoSel && (
                        <span className="rounded px-1.5 py-0.5 text-[11px] font-semibold" style={{ color: COR_NIVEL[riscoSel.nivel], background: `${COR_NIVEL[riscoSel.nivel]}1A` }}>
                          Risco 24h: {riscoSel.risco_24h}/100 ({ROTULO_NIVEL[riscoSel.nivel]})
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-ops-muted">{demandaSel.resumo}</p>
                    <p className="mt-1 text-[11px] text-ops-ciano">Local errado? Arraste o marcador no mapa.</p>
                    <div className="mt-2">
                      <ListaItens itens={visao === "preditiva" && riscoSel ? riscoSel.demanda_projetada : demandaSel.itens} />
                    </div>
                    {visao === "preditiva" && riscoSel && (
                      <ul className="mt-2 space-y-0.5 text-[11px] text-ops-muted">
                        {riscoSel.fatores.map((f) => (
                          <li key={f}>• {f}</li>
                        ))}
                      </ul>
                    )}
                    {demandaSel.transcricao && (
                      <p className="mt-2 border-l-2 border-ops-linha pl-2 text-[11px] italic text-ops-muted">&ldquo;{demandaSel.transcricao}&rdquo;</p>
                    )}
                  </>
                )}
                {doadorSel && (
                  <div className="mt-2">
                    <ListaItens itens={doadorSel.estoque} />
                    {!doadorSel.estoque.length && <p className="text-xs text-ops-muted">Estoque esgotado.</p>}
                  </div>
                )}
              </article>
            ) : (
              <div className="rounded-lg border border-ops-linha bg-ops-painel px-3 py-2 text-[11px] text-ops-muted">
                <p className="mb-1 font-semibold text-ops-texto">{visao === "atual" ? "Urgência relatada (1 a 5)" : "Risco previsto em 24h"}</p>
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                  {(visao === "atual"
                    ? [["5", COR_OPS.vermelho], ["4", COR_OPS.laranja], ["3", COR_OPS.ambar], ["1-2", COR_OPS.cinza]]
                    : [["Crítico", COR_NIVEL.critico], ["Alto", COR_NIVEL.alto], ["Moderado", COR_NIVEL.moderado], ["Baixo", COR_NIVEL.baixo]]
                  ).map(([r, c]) => (
                    <span key={r} className="flex items-center gap-1">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} aria-hidden />
                      {r}
                    </span>
                  ))}
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: COR_OPS.verde }} aria-hidden />
                    Doador
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="h-2.5 w-2.5 rounded-sm border-2" style={{ borderColor: COR_OPS.ciano }} aria-hidden />
                    Base
                  </span>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* ------------------------------------------------------------ esquerda */}
        <aside className="border-ops-linha bg-ops-painel lg:order-1 lg:overflow-y-auto lg:border-r">
          <PainelVoz llmAtivo={estado?.llm_ativo ?? false} onResultado={aoRelato} />
          <PainelRadar
            radar={radar}
            cenario={cenario}
            carregando={carregandoRadar}
            onCenario={aoCenario}
            onAlerta={(id) => setSelecao({ tipo: "demanda", id })}
          />
        </aside>

        {/* ------------------------------------------------------------ direita */}
        <aside className="border-ops-linha bg-ops-painel lg:order-3 lg:overflow-y-auto lg:border-l">
          <PainelRota
            rota={rota}
            desatualizada={rotaDesatualizada}
            modo={modoRota}
            maxEntregas={maxEntregas}
            gerando={gerando}
            concluindo={concluindo}
            onModo={setModoRota}
            onMaxEntregas={setMaxEntregas}
            onGerar={gerarRota}
            onConcluir={concluirRota}
            onParada={(p) =>
              p.tipo === "coleta"
                ? setSelecao({ tipo: "doador", id: p.ref_id })
                : p.tipo === "entrega"
                  ? setSelecao({ tipo: "demanda", id: p.ref_id })
                  : undefined
            }
          />
        </aside>
      </div>
    </div>
  );
}
