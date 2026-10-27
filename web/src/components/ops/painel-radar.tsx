"use client";

import { CloudLightning, CloudSun, Droplets, Radar as RadarIcon, Snowflake, Sun, Wind, type LucideIcon } from "lucide-react";

import { ROTULO_CATEGORIA } from "@/components/ops/cores";
import { Etiqueta, ICONE_CATEGORIA, Secao } from "@/components/ops/ui-ops";
import { useCidade } from "@/lib/cidade";
import type { CategoriaOps, Cenario, Radar } from "@/lib/types-ops";

const ICONE_CENARIO: Record<Cenario, LucideIcon> = {
  normal: CloudSun,
  frente_fria: Snowflake,
  tempestade: CloudLightning,
  onda_de_calor: Sun,
};

const FONTE = {
  "open-meteo": { rotulo: "Open-Meteo ao vivo", cor: "verde" },
  simulacao: { rotulo: "Simulação", cor: "ambar" },
  padrao: { rotulo: "Sem conexão: dia típico", cor: "muted" },
} as const;

/** Temperatura (linha) e chance de chuva (barras) nas próximas 24h. */
function Grafico24h({ radar }: { radar: Radar }) {
  const serie = radar.previsao.serie;
  if (serie.length < 2) return null;
  const L = 300;
  const A = 64;
  const min = Math.min(...serie.map((h) => h.temp)) - 1;
  const max = Math.max(...serie.map((h) => h.temp)) + 1;
  const x = (i: number) => (i / (serie.length - 1)) * L;
  const y = (t: number) => A - 8 - ((t - min) / (max - min)) * (A - 16);
  const linha = serie.map((h, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(h.temp).toFixed(1)}`).join(" ");
  const largura = L / serie.length - 1.5;

  return (
    <figure>
      <svg viewBox={`0 0 ${L} ${A}`} className="h-16 w-full" role="img" aria-label="Temperatura e chance de chuva nas próximas 24 horas">
        {serie.map((h, i) => (
          <rect
            key={i}
            x={(i / serie.length) * L}
            y={A - (h.chuva_prob / 100) * (A - 8)}
            width={largura}
            height={(h.chuva_prob / 100) * (A - 8)}
            rx={1}
            fill="#38BDF8"
            opacity={0.28}
          />
        ))}
        <path d={linha} fill="none" stroke="#22D3EE" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <figcaption className="mt-1 flex justify-between text-[10px] text-ops-muted">
        <span>{serie[0].hora}</span>
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-1"><span className="h-0.5 w-3 bg-ops-ciano" aria-hidden />temperatura</span>
          <span className="flex items-center gap-1"><span className="h-2 w-2 bg-sky-400/40" aria-hidden />chuva %</span>
        </span>
        <span>+24h</span>
      </figcaption>
    </figure>
  );
}

export function PainelRadar({
  radar,
  cenario,
  carregando,
  onCenario,
  onAlerta,
}: {
  radar: Radar | null;
  cenario: Cenario;
  carregando: boolean;
  onCenario: (c: Cenario) => void;
  onAlerta: (pontoId: number) => void;
}) {
  // Cada cidade só oferece cenários plausíveis (frente fria em Fortaleza não faz sentido).
  const { detalhe } = useCidade();
  const cenarios = [
    { valor: "normal" as Cenario, rotulo: "Previsão real" },
    ...(detalhe?.cenarios ?? []).map((c) => ({ valor: c.id as Cenario, rotulo: c.rotulo })),
  ];
  const p = radar?.previsao;
  const fonte = p ? FONTE[p.fonte] : null;

  return (
    <Secao
      icone={RadarIcon}
      titulo="Radar preditivo"
      subtitulo="Clima das próximas 24h × histórico dos pontos"
      acao={fonte && <Etiqueta cor={fonte.cor}>{fonte.rotulo}</Etiqueta>}
    >
      {p && radar ? (
        <>
          <div className={`flex items-end justify-between gap-3 transition-opacity ${carregando ? "opacity-50" : ""}`}>
            <div>
              <p className="font-display text-4xl font-semibold tabular-nums text-ops-texto">{Math.round(p.temp_agora)}°</p>
              <p className="text-xs text-ops-muted">
                mín {Math.round(p.temp_min_24h)}° · máx {Math.round(p.temp_max_24h)}°
              </p>
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <dt className="flex items-center gap-1 text-ops-muted"><Droplets className="h-3.5 w-3.5" aria-hidden />Chuva</dt>
              <dd className="text-right font-semibold tabular-nums text-ops-texto">{p.chuva_prob_max}% · {p.chuva_mm_24h.toLocaleString("pt-BR")} mm</dd>
              <dt className="flex items-center gap-1 text-ops-muted"><Wind className="h-3.5 w-3.5" aria-hidden />Vento</dt>
              <dd className="text-right font-semibold tabular-nums text-ops-texto">{Math.round(p.vento_max_kmh)} km/h</dd>
            </dl>
          </div>
          <div className="mt-3">
            <Grafico24h radar={radar} />
          </div>
        </>
      ) : (
        <div className="h-36 animate-pulse rounded-lg bg-ops-elevado" />
      )}

      <p className="mt-4 text-[11px] font-semibold uppercase tracking-wider text-ops-muted">Simular cenário</p>
      <div
        className="mt-2 grid gap-1.5"
        style={{ gridTemplateColumns: `repeat(${cenarios.length}, minmax(0, 1fr))` }}
        role="radiogroup"
        aria-label="Cenário climático"
      >
        {cenarios.map(({ valor, rotulo }) => {
          const Icone = ICONE_CENARIO[valor] ?? CloudSun;
          const ativo = cenario === valor;
          return (
            <button
              key={valor}
              role="radio"
              aria-checked={ativo}
              onClick={() => onCenario(valor)}
              className={`flex flex-col items-center gap-1 rounded-md border px-1.5 py-2 text-[11px] font-semibold leading-tight transition-colors ${
                ativo
                  ? valor === "normal"
                    ? "border-ops-ciano bg-ops-ciano/10 text-ops-ciano"
                    : "border-ops-ambar bg-ops-ambar/10 text-ops-ambar"
                  : "border-ops-linha bg-ops-elevado text-ops-muted hover:text-ops-texto"
              }`}
            >
              <Icone className="h-4 w-4" aria-hidden />
              {rotulo}
            </button>
          );
        })}
      </div>

      {radar && (
        <>
          <div className="mt-4">
            <div className="flex items-baseline justify-between text-xs">
              <span className="text-ops-muted">Índice de severidade climática</span>
              <span className="font-semibold tabular-nums text-ops-texto">{radar.indice_clima}/100</span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ops-linha">
              <div
                className="h-full rounded-full bg-gradient-to-r from-ops-ambar via-ops-laranja to-ops-vermelho transition-all duration-500"
                style={{ width: `${radar.indice_clima}%` }}
              />
            </div>
          </div>

          <p className="mt-4 text-[11px] font-semibold uppercase tracking-wider text-ops-muted">Demanda projetada em 24h</p>
          <ul className="mt-2 space-y-1.5">
            {(Object.entries(radar.aumento_projetado) as [CategoriaOps, number][]).map(([cat, pct]) => {
              const Icone = ICONE_CATEGORIA[cat];
              return (
                <li key={cat} className="grid grid-cols-[18px_1fr_52px] items-center gap-2 text-xs">
                  <Icone className="h-3.5 w-3.5 text-ops-muted" aria-hidden />
                  <span className="text-ops-texto">{ROTULO_CATEGORIA[cat]}</span>
                  <span className={`text-right font-semibold tabular-nums ${pct >= 50 ? "text-ops-vermelho" : pct >= 20 ? "text-ops-ambar" : "text-ops-muted"}`}>
                    +{pct}%
                  </span>
                </li>
              );
            })}
          </ul>

          <p className="mt-4 text-[11px] font-semibold uppercase tracking-wider text-ops-muted">Alertas</p>
          <ul className="mt-2 space-y-2">
            {radar.alertas.map((a) => {
              const cor = a.severidade === "critico" ? "border-l-ops-vermelho" : a.severidade === "atencao" ? "border-l-ops-ambar" : "border-l-ops-muted";
              const clicavel = a.pontos.length > 0;
              return (
                <li key={a.id}>
                  <button
                    disabled={!clicavel}
                    onClick={() => clicavel && onAlerta(a.pontos[0])}
                    className={`w-full rounded-md border border-ops-linha border-l-[3px] ${cor} bg-ops-bg p-2.5 text-left transition-colors enabled:hover:bg-ops-elevado`}
                  >
                    <p className="text-xs font-semibold text-ops-texto">{a.titulo}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-ops-muted">{a.descricao}</p>
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </Secao>
  );
}
