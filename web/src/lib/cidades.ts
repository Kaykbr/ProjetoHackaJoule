/** Cidades disponíveis. Módulo comum (sem "use client"): o layout do servidor também usa. */

export const CIDADES = [
  { id: "sp", nome: "São Paulo", curto: "SP", uf: "SP", lat: -23.5503, lng: -46.634 },
  { id: "rj", nome: "Rio de Janeiro", curto: "Rio", uf: "RJ", lat: -22.9068, lng: -43.1729 },
  { id: "for", nome: "Fortaleza", curto: "Fortaleza", uf: "CE", lat: -3.7275, lng: -38.5275 },
] as const;

export type CidadeId = (typeof CIDADES)[number]["id"];
export type Cidade = (typeof CIDADES)[number];

export const COOKIE_CIDADE = "cidade";

export function cidadeValida(valor: string | null | undefined): CidadeId | null {
  return CIDADES.some((c) => c.id === valor) ? (valor as CidadeId) : null;
}
