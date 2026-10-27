import type { CategoriaOps, NivelRisco, PontoDemanda, RiscoPonto } from "@/lib/types-ops";

/** Hex do tema escuro (Leaflet não lê classes do Tailwind). Mesmos valores de `ops.*`. */
export const COR_OPS = {
  ciano: "#22D3EE",
  verde: "#34D399",
  vermelho: "#F87171",
  laranja: "#FB923C",
  ambar: "#FBBF24",
  cinza: "#94A3B8",
} as const;

const POR_URGENCIA: Record<number, string> = {
  5: COR_OPS.vermelho,
  4: COR_OPS.laranja,
  3: COR_OPS.ambar,
  2: COR_OPS.cinza,
  1: "#64748B",
};

export const COR_NIVEL: Record<NivelRisco, string> = {
  critico: COR_OPS.vermelho,
  alto: COR_OPS.laranja,
  moderado: COR_OPS.ambar,
  baixo: COR_OPS.cinza,
};

export const ROTULO_NIVEL: Record<NivelRisco, string> = {
  critico: "Crítico",
  alto: "Alto",
  moderado: "Moderado",
  baixo: "Baixo",
};

export const ROTULO_CATEGORIA: Record<CategoriaOps, string> = {
  alimentacao: "Alimentação",
  agasalho: "Agasalho e abrigo",
  higiene: "Higiene",
  saude: "Saúde",
};

/** Condições vêm da API como slugs sem acento. */
export const ROTULO_CONDICAO: Record<string, string> = {
  chuva: "chuva",
  frio: "frio",
  criancas: "crianças",
  idosos: "idosos",
  feridos: "feridos",
  gestantes: "gestantes",
  mulheres: "mulheres",
  doentes: "doentes",
};

export function corDemanda(
  d: PontoDemanda,
  visao: "atual" | "preditiva",
  risco?: RiscoPonto,
): { cor: string; rotulo: string } {
  if (visao === "preditiva" && risco) {
    return { cor: COR_NIVEL[risco.nivel], rotulo: `risco ${risco.risco_24h}/100 em 24h` };
  }
  return { cor: POR_URGENCIA[d.urgencia] ?? COR_OPS.cinza, rotulo: `urgência ${d.urgencia}/5` };
}
