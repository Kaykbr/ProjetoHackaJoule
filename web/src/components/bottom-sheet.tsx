"use client";

import { useRef, useState, type ReactNode } from "react";

export type PosicaoSheet = "baixo" | "alto";

/**
 * Painel que sobe por cima do mapa no celular. Dois pontos de parada: espiando (mostra o
 * cabeçalho) e aberto. Arrastar ou tocar na alça alterna.
 */
export function BottomSheet({
  posicao,
  onPosicao,
  espiar = "11rem",
  children,
}: {
  posicao: PosicaoSheet;
  onPosicao: (p: PosicaoSheet) => void;
  espiar?: string;
  children: ReactNode;
}) {
  const [arrasto, setArrasto] = useState(0);
  const inicio = useRef<number | null>(null);

  const fim = () => {
    if (inicio.current === null) return;
    if (arrasto < -40) onPosicao("alto");
    else if (arrasto > 40) onPosicao("baixo");
    inicio.current = null;
    setArrasto(0);
  };

  const base = posicao === "alto" ? "0px" : `calc(100% - ${espiar})`;

  return (
    <div
      className="absolute inset-x-0 bottom-0 z-20 flex h-[88%] flex-col rounded-t-2xl border-t border-line bg-surface shadow-float"
      style={{
        transform: `translateY(calc(${base} + ${arrasto}px))`,
        transition: inicio.current === null ? "transform 200ms ease-out" : "none",
      }}
    >
      <button
        type="button"
        className="flex w-full touch-none justify-center pb-2 pt-3"
        aria-label={posicao === "alto" ? "Recolher lista" : "Expandir lista"}
        aria-expanded={posicao === "alto"}
        onClick={() => onPosicao(posicao === "alto" ? "baixo" : "alto")}
        onPointerDown={(e) => {
          inicio.current = e.clientY;
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => inicio.current !== null && setArrasto(e.clientY - inicio.current)}
        onPointerUp={fim}
        onPointerCancel={fim}
      >
        <span className="h-1.5 w-10 rounded-full bg-line" />
      </button>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{children}</div>
    </div>
  );
}
