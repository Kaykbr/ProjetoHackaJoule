"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
  ZoomControl,
} from "react-leaflet";

import { useCidade } from "@/lib/cidade";
import { NIVEL_COR, nivelMaisAlto } from "@/lib/format";
import { iconeEmCache, moverCamera, observarTamanho, posicao } from "@/lib/mapa-camera";
import type { PontoNoMapa } from "@/lib/mapa-dados";

type LatLng = { lat: number; lng: number };

export interface MapaProps {
  pontos: PontoNoMapa[];
  selecionado?: number | null;
  onSelecionar?: (pontoId: number) => void;
  doador?: LatLng | null;
  /** Desenha uma linha tracejada do doador até aqui (não é rota real). */
  destino?: LatLng | null;
  className?: string;
}

// Tiles do OSM (sem chave). A cor é neutralizada em globals.css (.leaflet-tile-pane), para que só
// a urgência tenha cor no mapa.
const TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATRIBUICAO = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

// `interactive={false}` vai como prop nos componentes: dentro de pathOptions o react-leaflet só
// aplica via setStyle, depois que o path já ganhou a classe `leaflet-interactive`.
const ESTILO_LINHA: L.PathOptions = { color: "#1F5F5B", weight: 3, dashArray: "6 8", opacity: 0.8 };
const ESTILO_DOADOR: L.PathOptions = { color: "#FFFFFF", weight: 3, fillColor: "#1F5F5B", fillOpacity: 1 };

function icone(cor: string, texto: string, ativo: boolean): L.DivIcon {
  return iconeEmCache(`p|${cor}|${texto}|${ativo}`, () => {
    const tamanho = ativo ? 40 : 30;
    const anel = ativo ? `box-shadow:0 0 0 4px ${cor}33, 0 2px 6px rgb(0 0 0 / .25);` : "box-shadow:0 1px 4px rgb(0 0 0 / .25);";
    return L.divIcon({
      className: "marcador-ponto",
      iconSize: [tamanho, tamanho],
      iconAnchor: [tamanho / 2, tamanho / 2],
      html: `<span style="display:grid;place-items:center;width:${tamanho}px;height:${tamanho}px;border-radius:9999px;background:${cor};color:#fff;font:600 ${ativo ? 15 : 13}px var(--font-sans),sans-serif;border:2px solid #fff;${anel}">${texto}</span>`,
    });
  });
}

/** Enquadra os pontos quando o conjunto muda e voa até o selecionado, sem voos concorrentes. */
function Controle({ pontos, selecionado, doador }: Pick<MapaProps, "pontos" | "selecionado" | "doador">) {
  const map = useMap();
  const chave = pontos.map((p) => p.ponto.id).join(",");

  // O container pode mudar de tamanho depois de montar (grid, sheet, animação): sem isso o
  // Leaflet fica com a medida antiga e não carrega os tiles.
  useEffect(() => observarTamanho(map), [map]);

  useEffect(() => {
    map.invalidateSize({ pan: false });
    const coords: [number, number][] = pontos.map((p) => [p.ponto.lat, p.ponto.lng]);
    if (doador) coords.push([doador.lat, doador.lng]);
    // Sem animação: assim não disputa com o voo até o selecionado, que pode vir no mesmo render.
    if (coords.length) moverCamera(map, () => map.fitBounds(coords, { padding: [48, 48], maxZoom: 15, animate: false }));
    // Só reenquadra quando o conjunto de pontos muda, não a cada render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, chave, doador?.lat, doador?.lng]);

  useEffect(() => {
    const alvo = pontos.find((p) => p.ponto.id === selecionado);
    if (!alvo) return;
    // Adia um quadro: deixa o enquadramento do mesmo render terminar antes de voar.
    const quadro = requestAnimationFrame(() =>
      moverCamera(map, () => {
        if (doador) {
          // Com doador no mapa, mostra os dois: de onde sai e para onde vai.
          map.flyToBounds(
            [
              [doador.lat, doador.lng],
              [alvo.ponto.lat, alvo.ponto.lng],
            ],
            { padding: [56, 56], maxZoom: 15, duration: 0.6 },
          );
        } else {
          map.flyTo([alvo.ponto.lat, alvo.ponto.lng], Math.max(map.getZoom(), 15), { duration: 0.6 });
        }
      }),
    );
    return () => cancelAnimationFrame(quadro);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, selecionado]);

  return null;
}

export default function Mapa({ pontos, selecionado, onSelecionar, doador, destino, className = "h-full w-full" }: MapaProps) {
  const { cidade } = useCidade();
  const marcadores = useMemo(
    () =>
      pontos.map(({ ponto, demandas }) => {
        const nivel = nivelMaisAlto(demandas.map((d) => d.urgencia.nivel));
        return { ponto, nivel, total: demandas.length };
      }),
    [pontos],
  );

  // Handlers estáveis por marcador: objeto novo a cada render fazia o react-leaflet religar eventos.
  const selecionarRef = useRef(onSelecionar);
  selecionarRef.current = onSelecionar;
  const handlers = useRef(new Map<number, L.LeafletEventHandlerFnMap>());
  const handlersPara = (id: number) => {
    let h = handlers.current.get(id);
    if (!h) {
      h = { click: () => selecionarRef.current?.(id) };
      handlers.current.set(id, h);
    }
    return h;
  };

  const linha = useMemo<[number, number][] | null>(
    () => (doador && destino ? [posicao(doador.lat, doador.lng), posicao(destino.lat, destino.lng)] : null),
    [doador?.lat, doador?.lng, destino?.lat, destino?.lng], // eslint-disable-line react-hooks/exhaustive-deps
  );

  return (
    <MapContainer
      center={[cidade.lat, cidade.lng]}
      zoom={13}
      scrollWheelZoom
      className={className}
      zoomControl={false}
      // Sem fade nos tiles: cada fade era um repaint a mais enquanto se arrasta o mapa.
      fadeAnimation={false}
    >
      <TileLayer attribution={ATRIBUICAO} url={TILES} />
      <ZoomControl position="bottomright" />
      <Controle pontos={pontos} selecionado={selecionado} doador={doador} />
      {linha && <Polyline positions={linha} pathOptions={ESTILO_LINHA} interactive={false} />}
      {marcadores.map(({ ponto, nivel, total }) => (
        <Marker
          key={ponto.id}
          position={posicao(ponto.lat, ponto.lng)}
          icon={icone(NIVEL_COR[nivel], String(total), ponto.id === selecionado)}
          title={`${ponto.nome}: ${total} pedido(s)`}
          zIndexOffset={ponto.id === selecionado ? 1000 : 0}
          eventHandlers={handlersPara(ponto.id)}
        >
          <Tooltip direction="top" offset={[0, -16]}>
            {ponto.nome}
          </Tooltip>
        </Marker>
      ))}
      {doador && (
        <CircleMarker center={posicao(doador.lat, doador.lng)} radius={8} pathOptions={ESTILO_DOADOR} interactive={false}>
          <Tooltip permanent direction="right" offset={[10, 0]}>
            Você
          </Tooltip>
        </CircleMarker>
      )}
    </MapContainer>
  );
}
