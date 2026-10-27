import { LoaderCircle } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variante = "primary" | "secondary" | "ghost" | "danger";
type Tamanho = "sm" | "md" | "lg";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50";

const VARIANTES: Record<Variante, string> = {
  primary: "bg-brand text-white hover:bg-brand-dark",
  secondary: "border border-line bg-surface text-ink hover:border-faint hover:bg-sunken",
  ghost: "text-muted hover:bg-sunken hover:text-ink",
  danger: "border border-line bg-surface text-urg-critica hover:border-urg-critica/40 hover:bg-red-50",
};

const TAMANHOS: Record<Tamanho, string> = {
  sm: "min-h-9 px-3 text-sm",
  md: "min-h-11 px-4 text-[15px]",
  lg: "min-h-12 px-5 text-base",
};

/** Classes de botão para usar também em `<Link>`. */
export function botao(variante: Variante = "primary", tamanho: Tamanho = "md", extra = ""): string {
  return `${BASE} ${VARIANTES[variante]} ${TAMANHOS[tamanho]} ${extra}`;
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  tamanho?: Tamanho;
  carregando?: boolean;
  icone?: ReactNode;
}

export function Button({
  variante = "primary",
  tamanho = "md",
  carregando = false,
  icone,
  className = "",
  children,
  disabled,
  type = "button",
  ...rest
}: Props) {
  return (
    <button
      type={type}
      className={botao(variante, tamanho, className)}
      disabled={disabled || carregando}
      aria-busy={carregando || undefined}
      {...rest}
    >
      {carregando ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden /> : icone}
      {children}
    </button>
  );
}
