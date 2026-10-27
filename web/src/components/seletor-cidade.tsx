"use client";

import { ChevronDown, MapPin } from "lucide-react";

import { useCidade } from "@/lib/cidade";
import { CIDADES, cidadeValida } from "@/lib/cidades";

/** Seletor nativo: acessível, funciona bem no celular e não precisa de JS de dropdown. */
export function SeletorCidade({ tema = "claro", className = "" }: { tema?: "claro" | "escuro"; className?: string }) {
  const { cidade, trocar } = useCidade();
  const cores =
    tema === "claro"
      ? "border-line bg-surface text-ink hover:border-brand/50"
      : "border-ops-linha bg-ops-elevado text-ops-texto hover:border-ops-ciano/60";
  return (
    <label className={`relative inline-flex items-center ${className}`}>
      <span className="sr-only">Cidade</span>
      <MapPin
        className={`pointer-events-none absolute left-2.5 h-3.5 w-3.5 ${tema === "claro" ? "text-brand" : "text-ops-ciano"}`}
        aria-hidden
      />
      <select
        value={cidade.id}
        onChange={(e) => {
          const id = cidadeValida(e.target.value);
          if (id) trocar(id);
        }}
        className={`h-9 cursor-pointer appearance-none rounded-lg border py-0 pl-7 pr-7 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 ${cores}`}
      >
        {CIDADES.map((c) => (
          <option key={c.id} value={c.id}>
            {c.nome}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 h-3.5 w-3.5 opacity-60" aria-hidden />
    </label>
  );
}
