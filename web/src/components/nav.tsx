"use client";

import { ChartBar, ClipboardList, HandHeart, Map as MapIcon, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { SeletorCidade } from "@/components/seletor-cidade";
import { botao } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

const LINKS: { href: string; rotulo: string; curto: string; icone: LucideIcon }[] = [
  { href: "/", rotulo: "Mapa de pedidos", curto: "Mapa", icone: MapIcon },
  { href: "/doar", rotulo: "Quero doar", curto: "Doar", icone: HandHeart },
  { href: "/ong", rotulo: "Sou ONG", curto: "ONG", icone: ClipboardList },
  { href: "/impacto", rotulo: "Impacto", curto: "Impacto", icone: ChartBar },
];

/** A central de operações tem layout próprio (tema escuro, tela cheia). */
function useEscondida(): boolean {
  return usePathname().startsWith("/operacao");
}

function useAtivo() {
  const pathname = usePathname();
  return (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
}

export function Nav() {
  const ativo = useAtivo();
  if (useEscondida()) return null;
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 px-4 sm:px-6 md:h-16 md:gap-6">
        <Link href="/" className="flex items-center gap-2.5" aria-label="Doa Certo, início">
          <Logo />
          <span className="font-display text-lg font-semibold tracking-tight">Doa Certo</span>
        </Link>
        <nav className="hidden flex-1 items-center gap-1 md:flex" aria-label="Principal">
          {LINKS.filter((l) => l.href !== "/doar").map((l) => (
            <Link
              key={l.href}
              href={l.href}
              aria-current={ativo(l.href) ? "page" : undefined}
              className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                ativo(l.href) ? "text-ink" : "text-muted hover:text-ink"
              }`}
            >
              <span className={ativo(l.href) ? "border-b-2 border-brand pb-1" : ""}>{l.rotulo}</span>
            </Link>
          ))}
        </nav>
        <SeletorCidade className="ml-auto md:ml-0" />
        <Link href="/doar" className={botao("primary", "sm", "hidden md:inline-flex")}>
          <HandHeart className="h-4 w-4" aria-hidden />
          Quero doar
        </Link>
      </div>
    </header>
  );
}

/** Navegação de app no celular: fixa embaixo, ao alcance do polegar. */
export function NavInferior() {
  const ativo = useAtivo();
  if (useEscondida()) return null;
  return (
    <nav
      aria-label="Principal"
      className="fixed inset-x-0 bottom-0 z-30 grid h-16 grid-cols-4 border-t border-line bg-surface md:hidden"
    >
      {LINKS.map(({ href, curto, icone: Icone }) => (
        <Link
          key={href}
          href={href}
          aria-current={ativo(href) ? "page" : undefined}
          className={`flex flex-col items-center justify-center gap-0.5 text-[11px] font-medium ${
            ativo(href) ? "text-brand" : "text-muted"
          }`}
        >
          <Icone className="h-5 w-5" aria-hidden />
          {curto}
        </Link>
      ))}
    </nav>
  );
}

export function Rodape() {
  return (
    <footer className="mt-auto border-t border-line">
      <div className="container-pg flex flex-col gap-2 py-6 text-xs text-muted sm:flex-row sm:items-center sm:justify-between">
        <p>Mostramos pontos de atendimento de ONGs, nunca a localização de pessoas.</p>
        <p>
          <Link href="/transparencia" className="font-medium text-ink underline-offset-2 hover:underline">
            Transparência e uso de IA
          </Link>{" "}
          · Mapa © OpenStreetMap. Clima por Open-Meteo. ONGs de demonstração são fictícias.
        </p>
      </div>
    </footer>
  );
}
