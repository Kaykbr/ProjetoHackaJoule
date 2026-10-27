/** Levar a rota para fora da tela: Google Maps, WhatsApp e texto copiável para o motorista. */
import type { Parada, RotaOtimizada } from "@/lib/types-ops";

/** O Google Maps aceita até 9 paradas intermediárias num link. */
const MAX_PARADAS_GOOGLE = 9;

const coord = (p: Parada) => `${p.lat},${p.lng}`;

export function linkGoogleMaps(rota: RotaOtimizada): { url: string; cortadas: number } {
  const [origem, ...resto] = rota.paradas;
  const destino = resto[resto.length - 1] ?? origem;
  const meio = resto.slice(0, -1);
  const cortadas = Math.max(0, meio.length - MAX_PARADAS_GOOGLE);
  const params = new URLSearchParams({
    api: "1",
    origin: coord(origem),
    destination: coord(destino),
    travelmode: "driving",
  });
  if (meio.length) params.set("waypoints", meio.slice(0, MAX_PARADAS_GOOGLE).map(coord).join("|"));
  return { url: `https://www.google.com/maps/dir/?${params}`, cortadas };
}

const VERBO: Record<Parada["tipo"], string> = {
  base: "Saída",
  coleta: "Coletar em",
  entrega: "Entregar em",
  retorno: "Voltar à base",
};

export function textoRoteiro(rota: RotaOtimizada, cidade: string): string {
  const linhas = [`Rota Doa Certo, ${cidade}: ${rota.distancia_km.toLocaleString("pt-BR")} km, ~${Math.round(rota.tempo_min)} min`];
  for (const p of rota.paradas) {
    const titulo = p.tipo === "retorno" ? VERBO.retorno : `${VERBO[p.tipo]} ${p.nome}`;
    const itens = p.itens.map((i) => `${i.quantidade} ${i.item}`).join(", ");
    linhas.push(`${p.ordem}. ${titulo}${itens ? `: ${itens}` : ""}`);
  }
  linhas.push("", `Mapa: ${linkGoogleMaps(rota).url}`);
  return linhas.join("\n");
}

export const linkWhatsApp = (texto: string) => `https://wa.me/?text=${encodeURIComponent(texto)}`;
