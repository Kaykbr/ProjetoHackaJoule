"use client";

import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Skeleton } from "@/components/ui/estado";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { plural } from "@/lib/format";
import type { Demanda, Impacto } from "@/lib/types";

interface Cobertura {
  nome: string;
  total: number;
  recebido: number;
  caminho: number;
}

function Numero({ valor, rotulo, vazio }: { valor: number | string; rotulo: string; vazio?: string }) {
  const zerado = valor === 0 && vazio;
  return (
    <div className="py-5 sm:px-6 sm:first:pl-0">
      {zerado ? (
        <p className="font-display text-base leading-snug text-muted sm:min-h-12">{vazio}</p>
      ) : (
        <p className="font-display text-4xl font-semibold tabular-nums sm:min-h-12 sm:text-5xl">
          {typeof valor === "number" ? valor.toLocaleString("pt-BR") : valor}
        </p>
      )}
      <p className="mt-1 text-sm text-muted">{rotulo}</p>
    </div>
  );
}

export default function ImpactoPage() {
  const toast = useToast();
  const [dados, setDados] = useState<Impacto | null>(null);
  const [demandas, setDemandas] = useState<Demanda[]>([]);

  useEffect(() => {
    Promise.all([api.impacto(), api.demandas({ status: "todas" })])
      .then(([i, d]) => {
        setDados(i);
        setDemandas(d);
      })
      .catch((e: Error) => toast({ tipo: "erro", titulo: "Não foi possível carregar", descricao: e.message }));
  }, [toast]);

  const cobertura = useMemo<Cobertura[]>(() => {
    const porCategoria = new Map<string, Cobertura>();
    for (const d of demandas) {
      if (d.status === "cancelada") continue;
      const c = porCategoria.get(d.categoria_nome) ?? { nome: d.categoria_nome, total: 0, recebido: 0, caminho: 0 };
      c.total += d.quantidade;
      c.recebido += d.quantidade_recebida;
      c.caminho += d.quantidade_prometida;
      porCategoria.set(d.categoria_nome, c);
    }
    return [...porCategoria.values()].sort((a, b) => b.total - a.total);
  }, [demandas]);

  return (
    <div className="container-pg py-10">
      <header className="max-w-2xl">
        <p className="eyebrow">Impacto</p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">Cada item chegou onde alguém tinha pedido.</h1>
        <p className="mt-3 text-muted">
          Contamos só o que as ONGs confirmaram. Nada de estimativa de &ldquo;pessoas impactadas&rdquo;.
        </p>
      </header>

      {/* ------------------------------------------------------------ números */}
      <section className="mt-8 grid grid-cols-2 divide-line border-y border-line sm:grid-cols-4 sm:divide-x" aria-label="Números">
        {dados ? (
          <>
            <Numero valor={dados.itens_entregues} rotulo="itens entregues" vazio="Ainda sem entregas confirmadas" />
            <Numero valor={dados.itens_prometidos} rotulo="itens a caminho" vazio="Nenhum item a caminho" />
            <Numero valor={dados.demandas_atendidas} rotulo={`pedidos atendidos de ${dados.demandas_abertas + dados.demandas_atendidas}`} vazio="Nenhum pedido completo ainda" />
            <Numero valor={dados.pontos} rotulo={`pontos de ${plural(dados.ongs, "ONG")}`} />
          </>
        ) : (
          Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="py-5 sm:px-6 sm:first:pl-0">
              <Skeleton className="h-12 w-20" />
              <Skeleton className="mt-2 h-3 w-24" />
            </div>
          ))
        )}
      </section>

      {/* ------------------------------------------------------------ cobertura */}
      <section className="mt-12 grid gap-8 lg:grid-cols-[280px_1fr]">
        <div>
          <h2 className="text-2xl font-semibold">Cobertura por categoria</h2>
          <p className="mt-2 text-sm text-muted">Quanto do que foi pedido já chegou ou está a caminho.</p>
          <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-brand" aria-hidden /> Recebido
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-brand/35" aria-hidden /> A caminho
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-sunken ring-1 ring-inset ring-line" aria-hidden /> Faltando
            </span>
          </div>
        </div>
        <ul className="space-y-4">
          {cobertura.map((c) => {
            const pct = (n: number) => (n / Math.max(1, c.total)) * 100;
            const coberto = Math.min(100, Math.round(pct(c.recebido + c.caminho)));
            return (
              <li key={c.nome} className="grid grid-cols-[96px_1fr_48px] items-center gap-3 text-sm sm:grid-cols-[120px_1fr_56px]">
                <span className="font-medium">{c.nome}</span>
                <span
                  className="flex h-3 overflow-hidden rounded-full bg-sunken"
                  role="img"
                  aria-label={`${c.nome}: ${c.recebido} recebidos, ${c.caminho} a caminho, de ${c.total}`}
                >
                  <span className="bg-brand" style={{ width: `${pct(c.recebido)}%` }} />
                  <span className="bg-brand/35" style={{ width: `${pct(c.caminho)}%` }} />
                </span>
                <span className="text-right tabular-nums text-muted">{coberto}%</span>
              </li>
            );
          })}
          {!cobertura.length &&
            Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-3 w-full" />)}
        </ul>
      </section>

      {/* ------------------------------------------------------------ confiança */}
      <section className="mt-14 border-t border-line pt-10" aria-labelledby="confianca-titulo">
        <div className="panel flex flex-col gap-5 p-5 sm:flex-row sm:p-6">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-brand-soft text-brand-dark">
            <ShieldCheck className="h-5 w-5" aria-hidden />
          </span>
          <div className="min-w-0">
            <h2 id="confianca-titulo" className="text-xl font-semibold">Onde entra a IA</h2>
            <ul className="mt-3 space-y-1.5 text-sm text-muted">
              <li>A IA só transforma as mensagens das ONGs em uma lista de itens. Quem publica é a ONG, depois de revisar.</li>
              <li>Telefones, e-mails e CPFs são removidos antes. O mapa mostra pontos de atendimento, nunca pessoas.</li>
              <li>A prioridade de cada pedido segue regras que qualquer pessoa pode conferir, e tudo funciona mesmo sem IA.</li>
            </ul>
            <Link href="/transparencia" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-brand hover:text-brand-dark">
              Como medimos o uso de IA
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
