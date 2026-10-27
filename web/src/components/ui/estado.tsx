import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-sunken ${className}`} aria-hidden />;
}

/** Lista de placeholders com a mesma silhueta das linhas reais. */
export function SkeletonLista({ linhas = 4 }: { linhas?: number }) {
  return (
    <div className="space-y-4" role="status" aria-label="Carregando">
      {Array.from({ length: linhas }, (_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
          <Skeleton className="h-1.5 w-full" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  icone: Icone,
  titulo,
  texto,
  acao,
}: {
  icone: LucideIcon;
  titulo: string;
  texto?: string;
  acao?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center px-6 py-10 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-full bg-sunken text-muted">
        <Icone className="h-5 w-5" aria-hidden />
      </span>
      <p className="mt-3 font-semibold">{titulo}</p>
      {texto && <p className="mt-1 max-w-xs text-sm text-muted">{texto}</p>}
      {acao && <div className="mt-4">{acao}</div>}
    </div>
  );
}
