"use client";

import { ArrowRight, HandHeart, MapPin, PackageOpen } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { BottomSheet, type PosicaoSheet } from "@/components/bottom-sheet";
import { ClimaFaixa } from "@/components/clima-banner";
import { ComoFunciona } from "@/components/como-funciona";
import { MapaDinamico } from "@/components/mapa-dinamico";
import { BadgeUrgencia } from "@/components/ui/badge-urgencia";
import { botao } from "@/components/ui/button";
import { Segmented } from "@/components/ui/controles";
import { EmptyState, SkeletonLista } from "@/components/ui/estado";
import { Progresso } from "@/components/ui/progresso";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { NIVEL_COR, NIVEL_LABEL, capitalizar, motivoPrincipal, plural } from "@/lib/format";
import { useMediaQuery } from "@/lib/hooks";
import { agruparPorPonto, type PontoNoMapa } from "@/lib/mapa-dados";
import type { Categoria, Clima, Demanda } from "@/lib/types";

const VISIVEIS_POR_PONTO = 3;

function GrupoPonto({
  grupo,
  ativo,
  onSelecionar,
}: {
  grupo: PontoNoMapa;
  ativo: boolean;
  onSelecionar: () => void;
}) {
  const [todos, setTodos] = useState(false);
  const ordenadas = [...grupo.demandas].sort((a, b) => b.urgencia.score - a.urgencia.score);
  const visiveis = todos ? ordenadas : ordenadas.slice(0, VISIVEIS_POR_PONTO);
  const { ponto } = grupo;

  return (
    <article
      className={`border-l-[3px] px-5 py-4 transition-colors ${
        ativo ? "border-l-brand bg-brand-soft/40" : "border-l-transparent hover:bg-sunken/60"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <button onClick={onSelecionar} className="min-w-0 text-left">
          <h3 className="font-sans text-base font-semibold leading-snug">{ponto.nome}</h3>
          <p className="mt-0.5 flex items-center gap-1 text-sm text-muted">
            <MapPin className="h-3.5 w-3.5 shrink-0" aria-hidden />
            <span className="truncate">
              {ponto.regiao}, {ponto.ong_nome}
            </span>
          </p>
        </button>
        <BadgeUrgencia nivel={ordenadas[0].urgencia.nivel} urgencia={ordenadas[0].urgencia} />
      </div>

      <ul className="mt-3 space-y-3">
        {visiveis.map((d) => (
          <LinhaDemanda key={d.id} demanda={d} />
        ))}
      </ul>

      {ordenadas.length > VISIVEIS_POR_PONTO && (
        <button className="link mt-3 text-sm" onClick={() => setTodos((t) => !t)}>
          {todos ? "Mostrar menos" : `Ver todos os ${ordenadas.length} pedidos`}
        </button>
      )}
    </article>
  );
}

function LinhaDemanda({ demanda }: { demanda: Demanda }) {
  const nivel = demanda.urgencia.nivel;
  return (
    <li>
      <div className="flex items-baseline justify-between gap-3">
        <p className="flex items-center gap-2 font-medium">
          <span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: NIVEL_COR[nivel] }} aria-hidden />
          {capitalizar(demanda.item)}
          <span className="sr-only">, urgência {NIVEL_LABEL[nivel]}</span>
        </p>
        <p className="shrink-0 text-sm tabular-nums text-muted">
          faltam <strong className="font-semibold text-ink">{demanda.faltam}</strong>
        </p>
      </div>
      <div className="mt-1.5 pl-4">
        <Progresso demanda={demanda} legenda={false} />
        <p className="mt-1 text-xs text-muted">{motivoPrincipal(demanda.urgencia.razoes)}</p>
      </div>
    </li>
  );
}

function PainelLista({
  carregando,
  demandas,
  grupos,
  categorias,
  filtro,
  onFiltro,
  selecionado,
  onSelecionar,
  refs,
}: {
  carregando: boolean;
  demandas: Demanda[];
  grupos: PontoNoMapa[];
  categorias: Categoria[];
  filtro: string;
  onFiltro: (f: string) => void;
  selecionado: number | null;
  onSelecionar: (id: number) => void;
  refs: React.MutableRefObject<Map<number, HTMLElement>>;
}) {
  const criticas = demandas.filter((d) => d.urgencia.nivel === "critica").length;
  const pontosComPedido = new Set(demandas.map((d) => d.ponto.id)).size;
  const opcoes = [
    { valor: "", rotulo: "Tudo" },
    ...categorias
      .filter((c) => demandas.some((d) => d.categoria === c.slug))
      .map((c) => ({ valor: c.slug, rotulo: c.nome })),
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="space-y-3 border-b border-line px-5 pb-4 pt-1 md:pt-5">
        <div>
          <h1 className="text-2xl font-semibold">Pedidos abertos</h1>
          <p className="mt-1 text-sm text-muted">
            {carregando ? (
              "Carregando pedidos…"
            ) : (
              <>
                {plural(demandas.length, "pedido")} em {plural(pontosComPedido, "ponto")} de atendimento.
                {criticas > 0 && (
                  <strong className="font-semibold text-urg-critica"> {plural(criticas, "crítico")}.</strong>
                )}
              </>
            )}
          </p>
        </div>
        <Segmented rotulo="Filtrar por categoria" tamanho="sm" opcoes={opcoes} valor={filtro} onChange={onFiltro} />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {carregando ? (
          <div className="p-5">
            <SkeletonLista />
          </div>
        ) : grupos.length === 0 ? (
          <EmptyState
            icone={PackageOpen}
            titulo="Nenhum pedido nesta categoria"
            texto="Quando uma ONG publicar, ele aparece aqui na hora."
            acao={
              <button className="link text-sm" onClick={() => onFiltro("")}>
                Ver todos os pedidos
              </button>
            }
          />
        ) : (
          <div className="divide-y divide-line">
            {grupos.map((g) => (
              <div
                key={g.ponto.id}
                ref={(el) => {
                  if (el) refs.current.set(g.ponto.id, el);
                  else refs.current.delete(g.ponto.id);
                }}
              >
                <GrupoPonto
                  grupo={g}
                  ativo={g.ponto.id === selecionado}
                  onSelecionar={() => onSelecionar(g.ponto.id)}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="hidden border-t border-line p-4 md:block">
        <Link href="/doar" className={botao("primary", "md", "w-full")}>
          <HandHeart className="h-4 w-4" aria-hidden />
          Tenho algo para doar
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </div>
  );
}

export default function MapaPage() {
  const toast = useToast();
  const desktop = useMediaQuery("(min-width: 768px)");
  const [demandas, setDemandas] = useState<Demanda[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [clima, setClima] = useState<Clima | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [filtro, setFiltro] = useState("");
  const [selecionado, setSelecionado] = useState<number | null>(null);
  const [sheet, setSheet] = useState<PosicaoSheet>("baixo");
  const refs = useRef(new Map<number, HTMLElement>());

  const carregar = useCallback(async () => {
    try {
      const [d, c, cl] = await Promise.all([api.demandas(), api.categorias(), api.clima()]);
      setDemandas(d);
      setCategorias(c);
      setClima(cl);
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não foi possível carregar os pedidos", descricao: (e as Error).message });
    } finally {
      setCarregando(false);
    }
  }, [toast]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const visiveis = useMemo(
    () => (filtro ? demandas.filter((d) => d.categoria === filtro) : demandas),
    [demandas, filtro],
  );
  // Pontos mais urgentes primeiro.
  const grupos = useMemo(
    () =>
      agruparPorPonto(visiveis).sort(
        (a, b) =>
          Math.max(...b.demandas.map((d) => d.urgencia.score)) - Math.max(...a.demandas.map((d) => d.urgencia.score)),
      ),
    [visiveis],
  );

  function selecionar(id: number) {
    setSelecionado(id);
    if (desktop === false) setSheet("alto");
    window.setTimeout(() => refs.current.get(id)?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 220);
  }

  const lista = (
    <PainelLista
      carregando={carregando}
      demandas={visiveis}
      grupos={grupos}
      categorias={categorias}
      filtro={filtro}
      onFiltro={setFiltro}
      selecionado={selecionado}
      onSelecionar={selecionar}
      refs={refs}
    />
  );

  return (
    // overflow-clip (não hidden): impede que foco/scrollIntoView da lista rolem o container inteiro.
    <div className="relative flex h-[calc(100dvh-3.5rem-4rem)] overflow-clip md:h-[calc(100dvh-4rem)]">
      {desktop && <aside className="w-[400px] shrink-0 border-r border-line bg-surface">{lista}</aside>}

      <section className="relative flex-1" aria-label="Mapa dos pontos de atendimento">
        <MapaDinamico pontos={grupos} selecionado={selecionado} onSelecionar={selecionar} />
        <div className="absolute inset-x-3 top-3 z-10 md:left-4 md:right-auto md:top-4 md:w-[380px]">
          <ClimaFaixa
            clima={clima}
            onChange={(c) => {
              setClima(c);
              void carregar();
            }}
          />
          <ComoFunciona />
        </div>
      </section>

      {desktop === false && (
        <BottomSheet posicao={sheet} onPosicao={setSheet}>
          {lista}
        </BottomSheet>
      )}
    </div>
  );
}
