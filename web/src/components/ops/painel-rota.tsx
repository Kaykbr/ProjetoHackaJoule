"use client";

import {
  CircleCheck,
  Clock,
  Copy,
  House,
  Leaf,
  LoaderCircle,
  MapPinned,
  MessageCircle,
  Minus,
  Package,
  PackageX,
  Plus,
  Route,
  Target,
  Truck,
  Undo2,
  type LucideIcon,
} from "lucide-react";

import { COR_OPS } from "@/components/ops/cores";
import { Etiqueta, ListaItens, Secao } from "@/components/ops/ui-ops";
import { useToast } from "@/components/ui/toast";
import { useCidade } from "@/lib/cidade";
import { linkGoogleMaps, linkWhatsApp, textoRoteiro } from "@/lib/roteiro";
import type { ModoRota, Parada, RotaOtimizada } from "@/lib/types-ops";

function duracao(min: number): string {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return h ? `${h}h ${m.toString().padStart(2, "0")}min` : `${m} min`;
}

function numero(v: number, casas = 1): string {
  return v.toLocaleString("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: casas });
}

const PARADA: Record<Parada["tipo"], { icone: LucideIcon; cor: string; verbo: string }> = {
  base: { icone: House, cor: COR_OPS.ciano, verbo: "Saída" },
  coleta: { icone: Package, cor: COR_OPS.verde, verbo: "Coletar" },
  entrega: { icone: Target, cor: COR_OPS.vermelho, verbo: "Entregar" },
  retorno: { icone: Undo2, cor: COR_OPS.ciano, verbo: "Retorno" },
};

function Metrica({ icone: Icone, rotulo, valor, detalhe }: { icone: LucideIcon; rotulo: string; valor: string; detalhe?: string }) {
  return (
    <div className="rounded-md border border-ops-linha bg-ops-bg p-2.5">
      <p className="flex items-center gap-1 text-[11px] text-ops-muted">
        <Icone className="h-3.5 w-3.5" aria-hidden />
        {rotulo}
      </p>
      <p className="mt-0.5 font-display text-xl font-semibold tabular-nums text-ops-texto">{valor}</p>
      {detalhe && <p className="text-[11px] leading-tight text-ops-muted">{detalhe}</p>}
    </div>
  );
}

const ACAO =
  "flex min-h-9 items-center justify-center gap-1.5 rounded-md border border-ops-linha bg-ops-elevado px-2 text-xs font-semibold text-ops-texto transition-colors hover:border-ops-ciano/60";

/** A rota sai da tela: vai para o celular do motorista. */
function LevarRota({ rota }: { rota: RotaOtimizada }) {
  const toast = useToast();
  const { cidade } = useCidade();
  const google = linkGoogleMaps(rota);
  const texto = textoRoteiro(rota, cidade.nome);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      toast({ tipo: "sucesso", titulo: "Roteiro copiado", descricao: "Cole no grupo da equipe ou no app de mensagens." });
    } catch {
      toast({ tipo: "erro", titulo: "Não deu para copiar", descricao: "O navegador bloqueou a área de transferência." });
    }
  }

  return (
    <div className="mt-4">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-ops-muted">Mandar para o motorista</p>
      <div className="mt-2 grid grid-cols-3 gap-1.5">
        <a href={google.url} target="_blank" rel="noopener noreferrer" className={ACAO}>
          <MapPinned className="h-3.5 w-3.5 text-ops-ciano" aria-hidden />
          Maps
        </a>
        <a href={linkWhatsApp(texto)} target="_blank" rel="noopener noreferrer" className={ACAO}>
          <MessageCircle className="h-3.5 w-3.5 text-ops-verde" aria-hidden />
          WhatsApp
        </a>
        <button onClick={() => void copiar()} className={ACAO}>
          <Copy className="h-3.5 w-3.5 text-ops-muted" aria-hidden />
          Copiar
        </button>
      </div>
      {google.cortadas > 0 && (
        <p className="mt-1.5 text-[11px] text-ops-muted">
          O Google Maps aceita 9 paradas por link; as {google.cortadas} últimas estão no roteiro de texto.
        </p>
      )}
    </div>
  );
}

export function PainelRota({
  rota,
  desatualizada = false,
  modo,
  maxEntregas,
  gerando,
  concluindo,
  onModo,
  onMaxEntregas,
  onGerar,
  onConcluir,
  onParada,
}: {
  rota: RotaOtimizada | null;
  /** Chegou relato depois que a rota foi gerada: ela não inclui o pedido novo. */
  desatualizada?: boolean;
  modo: ModoRota;
  maxEntregas: number;
  gerando: boolean;
  concluindo: boolean;
  onModo: (m: ModoRota) => void;
  onMaxEntregas: (n: number) => void;
  onGerar: () => void;
  onConcluir: () => void;
  onParada: (p: Parada) => void;
}) {
  return (
    <Secao icone={Route} titulo="Rota inteligente" subtitulo="Coleta nos doadores, entrega nos pontos críticos">
      <div className="grid grid-cols-2 gap-1.5" role="radiogroup" aria-label="Demanda usada na rota">
        {(
          [
            ["atual", "Demanda atual"],
            ["preditivo", "Previsão +24h"],
          ] as [ModoRota, string][]
        ).map(([valor, rotulo]) => (
          <button
            key={valor}
            role="radio"
            aria-checked={modo === valor}
            onClick={() => onModo(valor)}
            className={`rounded-md border px-2 py-1.5 text-xs font-semibold transition-colors ${
              modo === valor ? "border-ops-ciano bg-ops-ciano/10 text-ops-ciano" : "border-ops-linha bg-ops-elevado text-ops-muted hover:text-ops-texto"
            }`}
          >
            {rotulo}
          </button>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between text-xs">
        <span className="text-ops-muted">Pontos de entrega por rota</span>
        <span className="inline-flex items-center rounded-md border border-ops-linha">
          <button className="grid h-7 w-7 place-items-center text-ops-muted hover:text-ops-texto disabled:opacity-40" disabled={maxEntregas <= 1} onClick={() => onMaxEntregas(maxEntregas - 1)} aria-label="Menos pontos">
            <Minus className="h-3.5 w-3.5" aria-hidden />
          </button>
          <span className="w-6 text-center font-semibold tabular-nums text-ops-texto">{maxEntregas}</span>
          <button className="grid h-7 w-7 place-items-center text-ops-muted hover:text-ops-texto disabled:opacity-40" disabled={maxEntregas >= 8} onClick={() => onMaxEntregas(maxEntregas + 1)} aria-label="Mais pontos">
            <Plus className="h-3.5 w-3.5" aria-hidden />
          </button>
        </span>
      </div>

      <button
        onClick={onGerar}
        disabled={gerando}
        className="mt-3 flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-ops-ciano text-sm font-semibold text-ops-bg transition-colors hover:bg-white disabled:opacity-60"
      >
        {gerando ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden /> : <Route className="h-4 w-4" aria-hidden />}
        {gerando ? "Calculando a melhor rota…" : rota ? "Gerar nova rota" : "Gerar rota inteligente"}
      </button>

      {!rota && !gerando && (
        <p className="mt-4 text-center text-xs leading-relaxed text-ops-muted">
          O otimizador escolhe quais doadores têm o que os pontos mais urgentes precisam, ordena as paradas e traça a rota pelas ruas.
        </p>
      )}

      {rota && (
        <div className="mt-4 animate-fade-up">
          {desatualizada && rota.status === "planejada" && (
            <p className="mb-3 rounded-md border border-ops-ambar/30 bg-ops-ambar/5 p-2.5 text-xs text-ops-ambar">
              Chegou um relato depois desta rota, e ela ainda não inclui o pedido novo. Gere de novo para atualizar.
            </p>
          )}
          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            <Etiqueta cor={rota.fonte_rota === "osrm" ? "verde" : "ambar"}>
              {rota.fonte_rota === "osrm" ? "Rota real nas ruas (OSRM)" : "Estimativa (OSRM indisponível)"}
            </Etiqueta>
            {rota.modo === "preditivo" && <Etiqueta cor="ambar">Demanda prevista em 24h</Etiqueta>}
            {rota.status === "concluida" && <Etiqueta cor="verde">Concluída</Etiqueta>}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Metrica icone={Route} rotulo="Distância total" valor={`${numero(rota.distancia_km)} km`} detalhe="com retorno à base" />
            <Metrica icone={Clock} rotulo="Tempo estimado" valor={duracao(rota.tempo_min)} detalhe={`${rota.paradas.length - 2} paradas`} />
            <Metrica
              icone={Target}
              rotulo="Atendimento da demanda"
              valor={`${rota.taxa_atendimento_pct}%`}
              detalhe={`${rota.itens_entregues} itens, ${rota.pessoas_atendidas} pessoas`}
            />
            <Metrica
              icone={Leaf}
              rotulo="CO₂ evitado"
              valor={`${numero(rota.co2_evitado_kg)} kg`}
              detalhe={`${rota.viagens_evitadas} viagens de carro evitadas`}
            />
          </div>

          <p className="mt-4 text-[11px] font-semibold uppercase tracking-wider text-ops-muted">Roteiro do motorista</p>
          <ol className="relative mt-2">
            {rota.paradas.map((p, i) => {
              const { icone: Icone, cor, verbo } = PARADA[p.tipo];
              return (
                <li key={`${p.tipo}-${p.ordem}`} className="relative flex gap-3 pb-3 last:pb-0">
                  {i < rota.paradas.length - 1 && <span className="absolute left-[13px] top-7 h-[calc(100%-1.5rem)] w-px bg-ops-linha" aria-hidden />}
                  <span
                    className="relative grid h-7 w-7 shrink-0 place-items-center rounded-full border-2 bg-ops-bg"
                    style={{ borderColor: cor, color: cor }}
                  >
                    {p.tipo === "coleta" || p.tipo === "entrega" ? (
                      <span className="text-[11px] font-bold">{p.ordem}</span>
                    ) : (
                      <Icone className="h-3.5 w-3.5" aria-hidden />
                    )}
                  </span>
                  <button onClick={() => onParada(p)} className="min-w-0 flex-1 text-left">
                    <p className="flex items-baseline justify-between gap-2">
                      <span className="truncate text-sm font-semibold text-ops-texto">
                        <span className="mr-1 text-xs font-medium" style={{ color: cor }}>{verbo}</span>
                        {p.tipo === "retorno" ? "à base" : p.nome}
                      </span>
                      <span className="shrink-0 text-[11px] tabular-nums text-ops-muted">
                        {p.ordem === 0 ? "0 min" : `+${Math.round(p.chegada_min)} min`}
                      </span>
                    </p>
                    {p.ordem > 0 && <p className="text-[11px] text-ops-muted">{numero(p.distancia_desde_anterior_km)} km desde a parada anterior</p>}
                    {p.itens.length > 0 && (
                      <div className="mt-1.5">
                        <ListaItens itens={p.itens} verbo={verbo} />
                      </div>
                    )}
                  </button>
                </li>
              );
            })}
          </ol>

          {rota.nao_atendido.length > 0 && (
            <div className="mt-4 rounded-md border border-ops-ambar/30 bg-ops-ambar/5 p-2.5">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-ops-ambar">
                <PackageX className="h-3.5 w-3.5" aria-hidden />
                Sem estoque nos doadores
              </p>
              <ul className="mt-1.5 space-y-1.5">
                {rota.nao_atendido.map((p) => (
                  <li key={p.ponto_id} className="text-xs text-ops-muted">
                    <span className="text-ops-texto">{p.nome}:</span>{" "}
                    {p.itens.map((i) => `${i.quantidade} ${i.item}`).join(", ")}
                  </li>
                ))}
              </ul>
              <p className="mt-1.5 text-[11px] text-ops-muted">Vale uma campanha direcionada só para esses itens.</p>
            </div>
          )}

          {rota.status === "planejada" && <LevarRota rota={rota} />}

          {rota.status === "planejada" ? (
            <button
              onClick={onConcluir}
              disabled={concluindo}
              className="mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-ops-verde/50 bg-ops-verde/10 text-sm font-semibold text-ops-verde transition-colors hover:bg-ops-verde/20 disabled:opacity-60"
            >
              {concluindo ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden /> : <Truck className="h-4 w-4" aria-hidden />}
              Concluir entregas
            </button>
          ) : (
            <p className="mt-4 flex items-center justify-center gap-1.5 text-sm font-semibold text-ops-verde">
              <CircleCheck className="h-4 w-4" aria-hidden />
              Entregas registradas. Estoques e pedidos atualizados.
            </p>
          )}
        </div>
      )}
    </Secao>
  );
}
