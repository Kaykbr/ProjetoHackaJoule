"use client";

import dynamic from "next/dynamic";

/** Leaflet acessa `window`: o mapa só renderiza no navegador. */
export const MapaOpsDinamico = dynamic(() => import("@/components/ops/mapa-ops"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-ops-painel" />,
});
