"use client";

import { Check, CircleAlert, X } from "lucide-react";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

type Tipo = "sucesso" | "erro" | "info";

interface Toast {
  id: number;
  tipo: Tipo;
  titulo: string;
  descricao?: string;
  acao?: { rotulo: string; onClick: () => void };
}

type Novo = Omit<Toast, "id"> & { duracao?: number };

const Ctx = createContext<((t: Novo) => void) | null>(null);

export function useToast(): (t: Novo) => void {
  const fn = useContext(Ctx);
  if (!fn) throw new Error("useToast precisa estar dentro de <ToastProvider>.");
  return fn;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const proximo = useRef(1);

  const fechar = useCallback((id: number) => setToasts((l) => l.filter((t) => t.id !== id)), []);

  const mostrar = useCallback(
    ({ duracao, ...t }: Novo) => {
      const id = proximo.current++;
      setToasts((l) => [...l.slice(-2), { ...t, id }]);
      window.setTimeout(() => fechar(id), duracao ?? (t.tipo === "erro" ? 7000 : 4500));
    },
    [fechar],
  );

  return (
    <Ctx.Provider value={mostrar}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 md:bottom-6"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.tipo === "erro" ? "alert" : "status"}
            className="pointer-events-auto flex w-full max-w-md animate-fade-up items-start gap-3 rounded-xl bg-ink px-4 py-3 text-sm text-white shadow-float"
          >
            {t.tipo === "erro" ? (
              <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-300" aria-hidden />
            ) : (
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" aria-hidden />
            )}
            <div className="flex-1">
              <p className="font-semibold">{t.titulo}</p>
              {t.descricao && <p className="mt-0.5 text-white/75">{t.descricao}</p>}
            </div>
            {t.acao && (
              <button
                className="shrink-0 rounded px-1 font-semibold text-emerald-200 underline-offset-4 hover:underline"
                onClick={() => {
                  t.acao?.onClick();
                  fechar(t.id);
                }}
              >
                {t.acao.rotulo}
              </button>
            )}
            <button
              className="shrink-0 rounded text-white/60 hover:text-white"
              onClick={() => fechar(t.id)}
              aria-label="Fechar aviso"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
