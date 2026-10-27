import type { Nivel } from "@/lib/types";

export const NIVEL_LABEL: Record<Nivel, string> = {
  critica: "Crítica",
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

/** Hex usado no mapa (Leaflet não lê classes do Tailwind). Mesmos valores de `urg.*` no tailwind.config. */
export const NIVEL_COR: Record<Nivel, string> = {
  critica: "#B42318",
  alta: "#C4501C",
  media: "#B7791F",
  baixa: "#667085",
};

export const ORDEM_NIVEL: Nivel[] = ["critica", "alta", "media", "baixa"];

export function nivelMaisAlto(niveis: Nivel[]): Nivel {
  return ORDEM_NIVEL.find((n) => niveis.includes(n)) ?? "baixa";
}

/** "1 pedido" / "3 pedidos". */
export function plural(n: number, singular: string, pluralForma = `${singular}s`): string {
  return `${n.toLocaleString("pt-BR")} ${n === 1 ? singular : pluralForma}`;
}

/** "3 unidades de casaco" (o nome do item vem no singular da API). */
export function unidades(quantidade: number, item: string): string {
  return `${plural(quantidade, "unidade")} de ${item}`;
}

export function km(valor: number): string {
  if (valor < 0.1) return "menos de 100 m";
  return `${valor.toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 })} km`;
}

export function dataCurta(iso: string | null): string {
  if (!iso) return "";
  const [, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}`;
}

export function diasAte(iso: string): number {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const alvo = new Date(`${iso.slice(0, 10)}T00:00:00`);
  return Math.round((alvo.getTime() - hoje.getTime()) / 86_400_000);
}

export function prazoTexto(iso: string | null): string {
  if (!iso) return "Sem prazo";
  const dias = diasAte(iso);
  if (dias < 0) return "Prazo vencido";
  if (dias === 0) return "Até hoje";
  if (dias === 1) return "Até amanhã";
  return `Até ${dataCurta(iso)}`;
}

/**
 * A razão mais informativa para mostrar numa linha só.
 * Clima e prazo dizem mais ao doador do que "prioridade alta para a ONG".
 */
export function motivoPrincipal(razoes: string[]): string {
  const ordem = [/frio|calor/, /prazo/, /atendido/, /completa/];
  for (const padrao of ordem) {
    const achada = razoes.find((r) => padrao.test(r));
    if (achada) return capitalizar(achada);
  }
  return capitalizar(razoes[0] ?? "");
}

export function capitalizar(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

export function usd(valor: number): string {
  if (valor === 0) return "US$ 0";
  if (valor < 0.01) return `US$ ${valor.toLocaleString("pt-BR", { maximumSignificantDigits: 2 })}`;
  return `US$ ${valor.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}`;
}

