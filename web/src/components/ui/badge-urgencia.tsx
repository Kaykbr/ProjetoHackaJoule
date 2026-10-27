import { Circle, CircleAlert, OctagonAlert, TriangleAlert, type LucideIcon } from "lucide-react";

import { NIVEL_LABEL } from "@/lib/format";
import type { Nivel, Urgencia } from "@/lib/types";

const ICONE: Record<Nivel, LucideIcon> = {
  critica: OctagonAlert,
  alta: TriangleAlert,
  media: CircleAlert,
  baixa: Circle,
};

const ESTILO: Record<Nivel, string> = {
  critica: "bg-urg-critica text-white",
  alta: "bg-urg-alta/10 text-urg-alta ring-1 ring-inset ring-urg-alta/30",
  media: "bg-urg-media/10 text-urg-media ring-1 ring-inset ring-urg-media/30",
  baixa: "bg-sunken text-urg-baixa ring-1 ring-inset ring-line",
};

/**
 * Urgência com ícone e rótulo (não depende só de cor).
 * Com `urgencia`, vira um botão que mostra por que essa é a prioridade.
 */
export function BadgeUrgencia({ nivel, urgencia }: { nivel: Nivel; urgencia?: Urgencia }) {
  const Icone = ICONE[nivel];
  const conteudo = (
    <>
      <Icone className="h-3.5 w-3.5" aria-hidden />
      {NIVEL_LABEL[nivel]}
    </>
  );
  const classe = `inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-semibold ${ESTILO[nivel]}`;

  if (!urgencia) return <span className={classe}>{conteudo}</span>;

  return (
    <span className="group relative inline-flex">
      <button type="button" className={classe} aria-describedby={undefined}>
        {conteudo}
        <span className="sr-only">. Por que essa prioridade: {urgencia.razoes.join(", ")}</span>
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute right-0 top-full z-30 mt-1.5 hidden w-60 rounded-lg bg-ink p-3 text-left text-xs font-normal leading-snug text-white shadow-float group-hover:block group-focus-within:block"
      >
        <span className="mb-1 block font-semibold">Por que essa prioridade</span>
        {urgencia.razoes.map((r) => (
          <span key={r} className="block first-letter:uppercase">
            {r}
          </span>
        ))}
      </span>
    </span>
  );
}
