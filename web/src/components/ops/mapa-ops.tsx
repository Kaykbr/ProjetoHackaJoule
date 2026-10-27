"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { House, Package } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap, ZoomControl } from "react-leaflet";

import { corDemanda, COR_OPS } from "@/components/ops/cores";
import { iconeEmCache, moverCamera, observarTamanho, posicao } from "@/lib/mapa-camera";
import type { BaseOps, Doador, PontoDemanda, RiscoPonto, RotaOtimizada } from "@/lib/types-ops";

export type Visao = "atual" | "preditiva";
export type Selecao = { tipo: "demanda" | "doador"; id: number } | null;

export interface MapaOpsProps {
  base: BaseOps;
  demandas: PontoDemanda[];
  doadores: Doador[];
  visao: Visao;
  riscos: Map<number, RiscoPonto>;
  rota: RotaOtimizada | null;
  novos: Set<number>;
  selecao: Selecao;
  onSelecionar: (s: Selecao) => void;
  /** Ponto de demanda selecionado arrastado para o local certo. */
  onMover?: (id: number, lat: number, lng: number) => void;
}

const TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";

const ESTILO_BRILHO: L.PathOptions = { color: COR_OPS.ciano, weight: 12, opacity: 0.18 };
const ESTILO_LINHA: L.PathOptions = { color: COR_OPS.ciano, weight: 4, opacity: 0.95 };

function badge(ordem: number | undefined): string {
  if (ordem === undefined) return "";
  return `<span style="position:absolute;top:-8px;right:-8px;min-width:18px;height:18px;padding:0 4px;border-radius:9999px;background:${COR_OPS.ciano};color:#0A0F1A;font:700 11px/18px var(--font-sans),sans-serif;text-align:center;box-shadow:0 0 0 2px #0A0F1A">${ordem}</span>`;
}

function iconeDemanda(cor: string, texto: string, tamanho: number, pulsa: boolean, ativo: boolean, ordem?: number) {
  return iconeEmCache(`d|${cor}|${texto}|${tamanho}|${pulsa}|${ativo}|${ordem ?? ""}`, () => {
    const anel = pulsa ? `<span class="anel-pulso" style="color:${cor}"></span>` : "";
    const borda = ativo ? "#FFFFFF" : "#0A0F1A";
    return L.divIcon({
      className: "marcador-ponto",
      iconSize: [tamanho, tamanho],
      iconAnchor: [tamanho / 2, tamanho / 2],
      html: `<span style="position:relative;display:block;width:${tamanho}px;height:${tamanho}px;color:${cor}">${anel}<span style="position:relative;display:grid;place-items:center;width:100%;height:100%;border-radius:9999px;background:${cor};border:2px solid ${borda};box-shadow:0 0 18px ${cor}88;color:#0A0F1A;font:700 ${tamanho > 34 ? 13 : 12}px var(--font-sans),sans-serif">${texto}</span>${badge(ordem)}</span>`,
    });
  });
}

function iconeQuadrado(tipo: string, cor: string, svg: string, ativo: boolean, ordem?: number) {
  return iconeEmCache(`q|${tipo}|${ativo}|${ordem ?? ""}`, () =>
    L.divIcon({
      className: "marcador-ponto",
      iconSize: [28, 28],
      iconAnchor: [14, 14],
      html: `<span style="position:relative;display:grid;place-items:center;width:28px;height:28px;border-radius:8px;background:#0F1726;border:2px solid ${ativo ? "#FFFFFF" : cor};color:${cor};box-shadow:0 0 14px ${cor}66">${svg}${badge(ordem)}</span>`,
    }),
  );
}

const SVG_DOADOR = renderToStaticMarkup(<Package size={15} strokeWidth={2.2} />);
const SVG_BASE = renderToStaticMarkup(<House size={15} strokeWidth={2.2} />);

function Camera({ pontos, rota, selecao, demandas, doadores }: {
  pontos: [number, number][];
  rota: RotaOtimizada | null;
  selecao: Selecao;
  demandas: PontoDemanda[];
  doadores: Doador[];
}) {
  const map = useMap();
  const enquadrado = useRef(false);

  useEffect(() => observarTamanho(map), [map]);

  // Enquadra tudo UMA vez, ao abrir. Pontos novos chegam selecionados e o voo até eles cuida
  // do resto: reenquadrar aqui também disparava dois voos no mesmo render.
  useEffect(() => {
    if (enquadrado.current || !pontos.length) return;
    enquadrado.current = true;
    const quadro = requestAnimationFrame(() => {
      map.invalidateSize({ pan: false });
      moverCamera(map, () => map.fitBounds(pontos, { padding: [48, 48], maxZoom: 15, animate: false }));
    });
    return () => cancelAnimationFrame(quadro);
  }, [map, pontos]);

  useEffect(() => {
    if (!rota?.geometria.length) return;
    moverCamera(map, () => map.flyToBounds(rota.geometria, { padding: [40, 40], duration: 0.8 }));
  }, [map, rota]);

  useEffect(() => {
    if (!selecao) return;
    const alvo =
      selecao.tipo === "demanda"
        ? demandas.find((d) => d.id === selecao.id)
        : doadores.find((d) => d.id === selecao.id);
    if (alvo) moverCamera(map, () => map.flyTo([alvo.lat, alvo.lng], Math.max(map.getZoom(), 15), { duration: 0.6 }));
    // Só reage à mudança de seleção, não a cada atualização dos dados.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, selecao]);

  return null;
}

export default function MapaOps({
  base,
  demandas,
  doadores,
  visao,
  riscos,
  rota,
  novos,
  selecao,
  onSelecionar,
  onMover,
}: MapaOpsProps) {
  // Handlers estáveis por marcador: objeto novo a cada render fazia o react-leaflet religar eventos.
  const selecionarRef = useRef(onSelecionar);
  selecionarRef.current = onSelecionar;
  const moverRef = useRef(onMover);
  moverRef.current = onMover;
  const handlers = useRef(new Map<string, L.LeafletEventHandlerFnMap>());
  const handlersPara = (tipo: "demanda" | "doador", id: number) => {
    const chave = `${tipo}-${id}`;
    let h = handlers.current.get(chave);
    if (!h) {
      h = {
        click: () => selecionarRef.current({ tipo, id }),
        // Só dispara no ponto selecionado: é o único marcador arrastável.
        dragend: (e) => {
          const { lat, lng } = (e.target as L.Marker).getLatLng();
          moverRef.current?.(id, lat, lng);
        },
      };
      handlers.current.set(chave, h);
    }
    return h;
  };

  const ordem = useMemo(() => {
    const m = new Map<string, number>();
    rota?.paradas.forEach((p) => {
      if (p.tipo === "coleta" || p.tipo === "entrega") m.set(`${p.tipo}-${p.ref_id}`, p.ordem);
    });
    return m;
  }, [rota]);

  const pontos = useMemo<[number, number][]>(
    () => [[base.lat, base.lng], ...demandas.map((d) => [d.lat, d.lng] as [number, number]), ...doadores.map((d) => [d.lat, d.lng] as [number, number])],
    [base, demandas, doadores],
  );

  return (
    <MapContainer
      center={[base.lat, base.lng]}
      zoom={13}
      zoomControl={false}
      scrollWheelZoom
      // SVG (padrão), não Canvas: o renderizador Canvas do Leaflet 1.9 lança "clearRect of
      // undefined" quando o mapa remonta com um redesenho pendente.
      // Sem fade nos tiles: cada fade era um repaint a mais enquanto se arrasta o mapa.
      fadeAnimation={false}
      className="mapa-escuro h-full w-full"
    >
      <TileLayer url={TILES} attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' />
      <ZoomControl position="bottomright" />
      <Camera pontos={pontos} rota={rota} selecao={selecao} demandas={demandas} doadores={doadores} />

      {rota && (
        <>
          {/* A rota é só desenho. `interactive` e `smoothFactor` vão como props, não em pathOptions:
              o react-leaflet só repassa pathOptions via setStyle, depois de criar o path, e aí
              a classe `leaflet-interactive` já foi posta. Sem ela, a linha grossa de brilho para
              de capturar o mouse; smoothFactor simplifica os ~1.000 pontos do OSRM. */}
          <Polyline key={`brilho-${rota.id}`} positions={rota.geometria} pathOptions={ESTILO_BRILHO} interactive={false} smoothFactor={1.5} />
          <Polyline key={`linha-${rota.id}`} positions={rota.geometria} pathOptions={ESTILO_LINHA} interactive={false} smoothFactor={1.5} />
        </>
      )}

      <Marker position={posicao(base.lat, base.lng)} icon={iconeQuadrado("base", COR_OPS.ciano, SVG_BASE, false)} zIndexOffset={500}>
        <Tooltip direction="top" offset={[0, -14]}>
          Base: {base.nome}
        </Tooltip>
      </Marker>

      {doadores.map((d) => (
        <Marker
          key={`doador-${d.id}`}
          position={posicao(d.lat, d.lng)}
          icon={iconeQuadrado("doador", COR_OPS.verde, SVG_DOADOR, selecao?.tipo === "doador" && selecao.id === d.id, ordem.get(`coleta-${d.id}`))}
          eventHandlers={handlersPara("doador", d.id)}
        >
          <Tooltip direction="top" offset={[0, -14]}>
            {d.nome}: {d.total_itens} itens
          </Tooltip>
        </Marker>
      ))}

      {demandas.map((d) => {
        const risco = riscos.get(d.id);
        const { cor, rotulo } = corDemanda(d, visao, risco);
        const texto = visao === "preditiva" && risco ? String(risco.risco_24h) : String(d.urgencia);
        const tamanho = 26 + Math.min(16, Math.round(d.pessoas / 2.5));
        const pulsa = novos.has(d.id) || (visao === "preditiva" && risco?.nivel === "critico");
        const ativo = selecao?.tipo === "demanda" && selecao.id === d.id;
        return (
          <Marker
            key={`demanda-${d.id}`}
            position={posicao(d.lat, d.lng)}
            icon={iconeDemanda(cor, texto, tamanho, pulsa, ativo, ordem.get(`entrega-${d.id}`))}
            zIndexOffset={ativo ? 1000 : 100}
            draggable={ativo && Boolean(onMover)}
            eventHandlers={handlersPara("demanda", d.id)}
          >
            <Tooltip direction="top" offset={[0, -tamanho / 2]}>
              {d.nome}: {rotulo}
            </Tooltip>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
