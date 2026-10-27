"use client";

import { useEffect, useState } from "react";

/** `null` até montar no navegador; evita renderizar o layout errado no SSR. */
export function useMediaQuery(query: string): boolean | null {
  const [casa, setCasa] = useState<boolean | null>(null);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const atualizar = () => setCasa(mq.matches);
    atualizar();
    mq.addEventListener("change", atualizar);
    return () => mq.removeEventListener("change", atualizar);
  }, [query]);
  return casa;
}
