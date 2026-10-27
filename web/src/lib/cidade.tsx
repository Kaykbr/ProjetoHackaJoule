"use client";

/**
 * Cidade ativa (SP, RJ, Fortaleza): vale para o site inteiro e para a central.
 * Fica num cookie (o servidor já renderiza na cidade certa) e pode vir no link: `?cidade=rj`.
 * Trocar de cidade remonta as páginas, então cada uma recarrega os próprios dados.
 */
import { Fragment, createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, definirCidadeApi } from "@/lib/api";
import { CIDADES, COOKIE_CIDADE, cidadeValida, type Cidade, type CidadeId } from "@/lib/cidades";
import type { CidadeDetalhe } from "@/lib/types";

interface Contexto {
  cidade: Cidade;
  /** Cenários de clima e relatos de exemplo (de `GET /cidades`); `null` enquanto carrega. */
  detalhe: CidadeDetalhe | null;
  trocar: (id: CidadeId) => void;
}

const CidadeContext = createContext<Contexto | null>(null);

export function CidadeProvider({ inicial, children }: { inicial: CidadeId; children: React.ReactNode }) {
  const [id, setId] = useState<CidadeId>(inicial);
  const [detalhes, setDetalhes] = useState<CidadeDetalhe[]>([]);
  // Antes dos efeitos dos filhos: toda chamada à API já sai com a cidade certa.
  definirCidadeApi(id);

  const trocar = useCallback((novo: CidadeId) => {
    document.cookie = `${COOKIE_CIDADE}=${novo}; path=/; max-age=31536000; samesite=lax`;
    setId(novo);
  }, []);

  useEffect(() => {
    const doLink = cidadeValida(new URLSearchParams(window.location.search).get("cidade"));
    if (doLink && doLink !== id) trocar(doLink);
    api.cidades().then(setDetalhes).catch(() => undefined);
    // Só na primeira montagem: o link vale para a entrada no site.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cidade = CIDADES.find((c) => c.id === id) ?? CIDADES[0];
  const detalhe = detalhes.find((d) => d.id === id) ?? null;
  return (
    <CidadeContext.Provider value={{ cidade, detalhe, trocar }}>
      <Fragment key={id}>{children}</Fragment>
    </CidadeContext.Provider>
  );
}

export function useCidade(): Contexto {
  const ctx = useContext(CidadeContext);
  if (!ctx) throw new Error("useCidade precisa do CidadeProvider");
  return ctx;
}
