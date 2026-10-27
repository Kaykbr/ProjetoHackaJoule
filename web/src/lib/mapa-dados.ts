import type { Demanda, Ponto } from "@/lib/types";

/** Fica fora de components/mapa.tsx: importar aquele arquivo puxa o Leaflet para o SSR. */
export interface PontoNoMapa {
  ponto: Ponto;
  demandas: Demanda[];
}

export function agruparPorPonto(demandas: Demanda[]): PontoNoMapa[] {
  const mapa = new Map<number, PontoNoMapa>();
  for (const d of demandas) {
    const atual = mapa.get(d.ponto.id) ?? { ponto: d.ponto, demandas: [] };
    atual.demandas.push(d);
    mapa.set(d.ponto.id, atual);
  }
  return [...mapa.values()];
}
