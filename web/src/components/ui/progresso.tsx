import type { Demanda } from "@/lib/types";

/** Barra recebido (cheio) + a caminho (hachurado) sobre o total pedido. */
export function Progresso({ demanda, legenda = true }: { demanda: Demanda; legenda?: boolean }) {
  const pct = (n: number) => `${Math.min(100, (n / Math.max(1, demanda.quantidade)) * 100)}%`;
  return (
    <div>
      <div
        className="flex h-1.5 overflow-hidden rounded-full bg-sunken"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={demanda.quantidade}
        aria-valuenow={demanda.quantidade_recebida + demanda.quantidade_prometida}
        aria-label={`${demanda.quantidade - demanda.faltam} de ${demanda.quantidade} cobertos`}
      >
        <div className="bg-brand" style={{ width: pct(demanda.quantidade_recebida) }} />
        <div
          className="bg-brand/35"
          style={{
            width: pct(demanda.quantidade_prometida),
            backgroundImage:
              "repeating-linear-gradient(135deg, transparent 0 3px, rgb(255 255 255 / 0.5) 3px 5px)",
          }}
        />
      </div>
      {legenda && (
        <p className="mt-1 text-xs text-muted">
          <strong className="font-semibold text-ink">Faltam {demanda.faltam}</strong> de {demanda.quantidade}
          {demanda.quantidade_prometida > 0 && <>, {demanda.quantidade_prometida} a caminho</>}
        </p>
      )}
    </div>
  );
}
