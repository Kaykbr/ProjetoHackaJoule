import { History, ShieldCheck, Sparkles, WifiOff, Zap, type LucideIcon } from "lucide-react";
import Link from "next/link";

import { plural } from "@/lib/format";
import type { OrigemIA } from "@/lib/types";

/** Como a mensagem foi lida. Mesmo texto no site e na central de operações. */
export const ORIGEM: Record<OrigemIA, { rotulo: string; icone: LucideIcon; gratis: boolean }> = {
  llm: { rotulo: "Lido por IA", icone: Sparkles, gratis: false },
  regras: { rotulo: "Texto simples, lido sem IA", icone: Zap, gratis: true },
  cache: { rotulo: "Já lido antes, sem nova chamada", icone: History, gratis: true },
  fallback: { rotulo: "Regras locais (IA indisponível)", icone: WifiOff, gratis: true },
};

/** Linha discreta sob o título da revisão: origem, dados pessoais barrados e link explicativo. */
export function SeloOrigem({ origem, pii, descartados }: { origem: OrigemIA; pii: number; descartados: number }) {
  const { rotulo, icone: Icone } = ORIGEM[origem];
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
      <span className={`inline-flex items-center gap-1.5 ${origem === "fallback" ? "text-urg-media" : ""}`}>
        <Icone className="h-3.5 w-3.5" aria-hidden />
        {rotulo}
      </span>
      {pii > 0 && (
        <span className="inline-flex items-center gap-1.5 font-medium text-brand">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
          {plural(pii, "dado pessoal removido", "dados pessoais removidos")} antes do envio
        </span>
      )}
      {descartados > 0 && (
        <span className="inline-flex items-center gap-1.5 font-medium text-urg-media">
          {plural(descartados, "item ignorado", "itens ignorados")}: não aparecia na mensagem
        </span>
      )}
      <Link href="/impacto" className="link">
        Como usamos IA
      </Link>
    </p>
  );
}

/** Trecho da mensagem que justifica o item. */
export function Evidencia({ texto }: { texto: string }) {
  if (!texto) return null;
  return (
    <p className="truncate text-xs italic text-muted" title={texto}>
      <span className="sr-only">Trecho da mensagem: </span>&ldquo;{texto}&rdquo;
    </p>
  );
}
