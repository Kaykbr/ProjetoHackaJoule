"use client";

import { Check, Minus, Plus } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

/** Label + controle + dica. Mantém o espaçamento e a acessibilidade iguais em todo formulário. */
export function Field({
  id,
  label,
  dica,
  children,
}: {
  id: string;
  label: string;
  dica?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      {children}
      {dica && <p className="mt-1.5 text-xs text-muted">{dica}</p>}
    </div>
  );
}

export interface Opcao<T extends string | number> {
  valor: T;
  rotulo: ReactNode;
}

/** Controle segmentado: abas, filtros e escolhas curtas. Rola na horizontal no celular. */
export function Segmented<T extends string | number>({
  opcoes,
  valor,
  onChange,
  rotulo,
  tamanho = "md",
}: {
  opcoes: Opcao<T>[];
  valor: T;
  onChange: (v: T) => void;
  rotulo: string;
  tamanho?: "sm" | "md";
}) {
  return (
    <div
      role="tablist"
      aria-label={rotulo}
      className="-mx-1 flex max-w-full gap-1 overflow-x-auto px-1 [scrollbar-width:none]"
    >
      <div className="inline-flex gap-1 rounded-lg bg-sunken p-1">
        {opcoes.map((o) => {
          const ativo = o.valor === valor;
          return (
            <button
              key={String(o.valor)}
              role="tab"
              aria-selected={ativo}
              onClick={() => onChange(o.valor)}
              className={`whitespace-nowrap rounded-md font-medium transition-colors ${
                tamanho === "sm" ? "px-2.5 py-1 text-xs" : "px-3 py-1.5 text-sm"
              } ${ativo ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink"}`}
            >
              {o.rotulo}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** Quantidade com − / + (alvos de toque grandes) e digitação livre. */
export function Quantidade({
  id,
  valor,
  onChange,
  destaque = false,
  rotulo = "Quantidade",
}: {
  id?: string;
  valor: number;
  onChange: (v: number) => void;
  destaque?: boolean;
  rotulo?: string;
}) {
  const borda = destaque ? "border-urg-media bg-urg-media/5" : "border-line bg-surface";
  return (
    <div className={`inline-flex items-stretch rounded-lg border ${borda}`}>
      <button
        type="button"
        className="grid w-10 place-items-center text-muted hover:text-ink disabled:opacity-40"
        onClick={() => onChange(Math.max(1, valor - 1))}
        disabled={valor <= 1}
        aria-label="Diminuir"
      >
        <Minus className="h-4 w-4" aria-hidden />
      </button>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        min={1}
        aria-label={rotulo}
        className="w-14 border-x border-inherit bg-transparent py-2 text-center text-[15px] font-semibold tabular-nums [appearance:textfield] focus:outline-none [&::-webkit-inner-spin-button]:appearance-none"
        value={valor}
        onChange={(e) => onChange(Math.max(1, Number(e.target.value) || 1))}
      />
      <button
        type="button"
        className="grid w-10 place-items-center text-muted hover:text-ink"
        onClick={() => onChange(valor + 1)}
        aria-label="Aumentar"
      >
        <Plus className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}

/** Etapas numeradas (ex.: fluxo do doador). */
export function Stepper({ etapas, atual }: { etapas: string[]; atual: number }) {
  return (
    <ol className="flex items-center gap-2 text-sm">
      {etapas.map((nome, i) => {
        const feito = i < atual;
        const ativo = i === atual;
        return (
          <li key={nome} className="flex items-center gap-2" aria-current={ativo ? "step" : undefined}>
            <span
              className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-semibold ${
                feito ? "bg-brand text-white" : ativo ? "bg-ink text-white" : "bg-sunken text-muted"
              }`}
            >
              {feito ? <Check className="h-3.5 w-3.5" aria-hidden /> : i + 1}
            </span>
            <span className={`hidden sm:inline ${ativo ? "font-semibold text-ink" : "text-muted"}`}>{nome}</span>
            {i < etapas.length - 1 && <span className="h-px w-6 bg-line sm:w-10" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}

/** Menu suspenso simples (fecha ao clicar fora ou com Esc). */
export function Menu({
  gatilho,
  rotulo,
  children,
  alinhar = "right",
}: {
  gatilho: ReactNode;
  rotulo: string;
  children: (fechar: () => void) => ReactNode;
  alinhar?: "left" | "right";
}) {
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setAberto(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false);
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", fora);
      document.removeEventListener("keydown", esc);
    };
  }, [aberto]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={rotulo}
        aria-haspopup="menu"
        aria-expanded={aberto}
        onClick={() => setAberto((a) => !a)}
        className="inline-flex min-h-9 items-center gap-1.5 rounded-lg px-2 text-sm font-medium text-muted hover:bg-sunken hover:text-ink"
      >
        {gatilho}
      </button>
      {aberto && (
        <div
          role="menu"
          className={`absolute top-full z-40 mt-1 min-w-56 animate-fade-up rounded-xl border border-line bg-surface p-1 shadow-float ${
            alinhar === "right" ? "right-0" : "left-0"
          }`}
        >
          {children(() => setAberto(false))}
        </div>
      )}
    </div>
  );
}

export function MenuItem({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      role="menuitem"
      onClick={onClick}
      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-sunken"
    >
      {children}
    </button>
  );
}
