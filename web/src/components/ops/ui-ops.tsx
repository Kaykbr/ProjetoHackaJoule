import { HeartPulse, Shirt, Droplet, UtensilsCrossed, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { ROTULO_CATEGORIA } from "@/components/ops/cores";
import type { CategoriaOps, ItemOps } from "@/lib/types-ops";

export const ICONE_CATEGORIA: Record<CategoriaOps, LucideIcon> = {
  alimentacao: UtensilsCrossed,
  agasalho: Shirt,
  higiene: Droplet,
  saude: HeartPulse,
};

export function Secao({
  icone: Icone,
  titulo,
  subtitulo,
  acao,
  children,
}: {
  icone: LucideIcon;
  titulo: string;
  subtitulo?: string;
  acao?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="border-b border-ops-linha p-4">
      <header className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-ops-elevado text-ops-ciano">
            <Icone className="h-4 w-4" aria-hidden />
          </span>
          <div>
            <h2 className="font-sans text-sm font-semibold text-ops-texto">{titulo}</h2>
            {subtitulo && <p className="text-xs text-ops-muted">{subtitulo}</p>}
          </div>
        </div>
        {acao}
      </header>
      {children}
    </section>
  );
}

export function Etiqueta({ children, cor = "muted" }: { children: ReactNode; cor?: "muted" | "ciano" | "verde" | "vermelho" | "ambar" }) {
  const estilo = {
    muted: "bg-ops-elevado text-ops-muted",
    ciano: "bg-ops-ciano/10 text-ops-ciano",
    verde: "bg-ops-verde/10 text-ops-verde",
    vermelho: "bg-ops-vermelho/10 text-ops-vermelho",
    ambar: "bg-ops-ambar/10 text-ops-ambar",
  }[cor];
  return <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium ${estilo}`}>{children}</span>;
}

export function ListaItens({ itens, verbo }: { itens: (ItemOps & { evidencia?: string })[]; verbo?: string }) {
  if (!itens.length) return null;
  return (
    <ul className="flex flex-wrap gap-1.5">
      {itens.map((i) => {
        const Icone = ICONE_CATEGORIA[i.categoria];
        return (
          <li
            key={`${i.categoria}-${i.item}`}
            title={i.evidencia ? `${ROTULO_CATEGORIA[i.categoria]}: “${i.evidencia}”` : ROTULO_CATEGORIA[i.categoria]}
            className="inline-flex items-center gap-1 rounded-md border border-ops-linha bg-ops-bg px-1.5 py-0.5 text-xs text-ops-texto"
          >
            <Icone className="h-3 w-3 text-ops-muted" aria-hidden />
            {verbo && <span className="sr-only">{verbo} </span>}
            <span className="tabular-nums font-semibold">{i.quantidade}</span> {i.item}
          </li>
        );
      })}
    </ul>
  );
}

/** Urgência 1–5 como barrinhas (não depende só de cor: o número vai junto). */
export function Urgencia({ valor }: { valor: number }) {
  const cor = valor >= 5 ? "bg-ops-vermelho" : valor >= 4 ? "bg-ops-laranja" : valor >= 3 ? "bg-ops-ambar" : "bg-ops-muted";
  return (
    <span className="inline-flex items-center gap-1.5" aria-label={`Urgência ${valor} de 5`}>
      <span className="flex gap-0.5" aria-hidden>
        {[1, 2, 3, 4, 5].map((n) => (
          <span key={n} className={`h-2.5 w-1.5 rounded-sm ${n <= valor ? cor : "bg-ops-linha"}`} />
        ))}
      </span>
      <span className="text-xs font-semibold tabular-nums text-ops-texto">{valor}/5</span>
    </span>
  );
}
