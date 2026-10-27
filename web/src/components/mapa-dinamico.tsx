"use client";

import dynamic from "next/dynamic";

/** Leaflet acessa `window`: só pode renderizar no navegador. */
export const MapaDinamico = dynamic(() => import("@/components/mapa"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-sunken" />,
});
