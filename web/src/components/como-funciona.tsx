"use client";

import { HandHeart, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { botao } from "@/components/ui/button";
import { useCidade } from "@/lib/cidade";

const CHAVE = "doacerto-como-funciona-visto";

const PASSOS = [
  "ONGs publicam o que falta em cada ponto de atendimento.",
  "Você diz o que tem e indicamos o pedido mais perto que precisa disso.",
  "Você entrega e a ONG confirma. O pedido some do mapa.",
];

/** Cartão da primeira visita. Some ao fechar e não volta (fica lembrado no navegador). */
export function ComoFunciona() {
  const { cidade } = useCidade();
  const [visivel, setVisivel] = useState(false);

  useEffect(() => {
    try {
      setVisivel(localStorage.getItem(CHAVE) !== "1");
    } catch {
      setVisivel(true);
    }
  }, []);

  function fechar() {
    setVisivel(false);
    try {
      localStorage.setItem(CHAVE, "1");
    } catch {
      /* armazenamento bloqueado: volta a aparecer na próxima visita */
    }
  }

  if (!visivel) return null;
  return (
    <section
      aria-labelledby="como-funciona-titulo"
      className="relative mt-2 animate-fade-up rounded-xl border border-line bg-surface p-4 shadow-float"
    >
      <button
        onClick={fechar}
        aria-label="Fechar"
        className="absolute right-2 top-2 rounded-md p-1.5 text-muted hover:bg-sunken hover:text-ink"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
      <h2 id="como-funciona-titulo" className="pr-8 font-display text-lg font-semibold leading-snug">
        A doação certa, no lugar certo
      </h2>
      <p className="mt-0.5 text-xs text-muted">Pedidos reais de ONGs em {cidade.nome}.</p>
      <ol className="mt-3 space-y-2">
        {PASSOS.map((passo, i) => (
          <li key={passo} className="flex gap-2.5 text-sm">
            <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-soft text-[11px] font-semibold text-brand-dark">
              {i + 1}
            </span>
            {passo}
          </li>
        ))}
      </ol>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href="/doar" onClick={fechar} className={botao("primary", "sm")}>
          <HandHeart className="h-4 w-4" aria-hidden />
          Quero doar
        </Link>
        <Link href="/ong" onClick={fechar} className={botao("secondary", "sm")}>
          Sou de uma ONG
        </Link>
      </div>
    </section>
  );
}
