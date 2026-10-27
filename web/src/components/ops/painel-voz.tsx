"use client";

import { LoaderCircle, MapPin, Mic, Radio, ShieldCheck, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ROTULO_CONDICAO } from "@/components/ops/cores";
import { Etiqueta, ListaItens, Secao, Urgencia } from "@/components/ops/ui-ops";
import { ORIGEM } from "@/components/ui/selo-origem";
import { useToast } from "@/components/ui/toast";
import { ops } from "@/lib/api";
import { useCidade } from "@/lib/cidade";
import type { RelatoResultado } from "@/lib/types-ops";

const FONTE_GEO = { dicionario: "Lugar conhecido", nominatim: "OpenStreetMap", centro: "Local não encontrado" } as const;

// Web Speech API: não faz parte da lib DOM do TypeScript.
interface Reconhecimento {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}

function construtorReconhecimento(): (new () => Reconhecimento) | null {
  const w = window as unknown as { SpeechRecognition?: new () => Reconhecimento; webkitSpeechRecognition?: new () => Reconhecimento };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

type Estado = "parado" | "ouvindo" | "gravando" | "enviando";

export function PainelVoz({ llmAtivo, onResultado }: { llmAtivo: boolean; onResultado: (r: RelatoResultado) => void }) {
  const toast = useToast();
  // Relatos prontos da cidade: um clique e o ponto aparece no mapa.
  const relatosProntos = useCidade().detalhe?.relatos_exemplo ?? [];
  const [estado, setEstado] = useState<Estado>("parado");
  const [falado, setFalado] = useState("");
  const [parcial, setParcial] = useState("");
  const [texto, setTexto] = useState("");
  const [resultado, setResultado] = useState<RelatoResultado | null>(null);
  const reconhecimento = useRef<Reconhecimento | null>(null);
  const gravador = useRef<MediaRecorder | null>(null);
  const finalRef = useRef("");

  useEffect(() => () => reconhecimento.current?.stop(), []);

  async function enviar(conteudo: string | Blob) {
    setEstado("enviando");
    try {
      const r = typeof conteudo === "string" ? await ops.relato(conteudo) : await ops.relatoAudio(conteudo);
      setResultado(r);
      onResultado(r);
      setTexto("");
      toast({
        tipo: "sucesso",
        titulo: r.acao === "criado" ? `Novo ponto: ${r.ponto.nome}` : `Ponto atualizado: ${r.ponto.nome}`,
        descricao: `${r.ponto.pessoas} pessoas, urgência ${r.ponto.urgencia}/5.`,
      });
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não deu para processar o relato", descricao: (e as Error).message });
    } finally {
      setEstado("parado");
      setParcial("");
    }
  }

  async function gravarAudio() {
    if (!llmAtivo || typeof MediaRecorder === "undefined" || !navigator.mediaDevices) {
      toast({ tipo: "erro", titulo: "Gravação indisponível", descricao: "Use o Chrome para ditar, ou digite o relato." });
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const partes: Blob[] = [];
      rec.ondataavailable = (e) => partes.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        void enviar(new Blob(partes, { type: rec.mimeType || "audio/webm" }));
      };
      gravador.current = rec;
      rec.start();
      setEstado("gravando");
    } catch {
      toast({ tipo: "erro", titulo: "Sem acesso ao microfone", descricao: "Libere o microfone no navegador ou digite o relato." });
    }
  }

  function alternarMicrofone() {
    if (estado === "ouvindo") return reconhecimento.current?.stop();
    if (estado === "gravando") return gravador.current?.stop();
    if (estado !== "parado") return;

    const Construtor = construtorReconhecimento();
    if (!Construtor) return void gravarAudio();

    const r = new Construtor();
    r.lang = "pt-BR";
    r.continuous = true;
    r.interimResults = true;
    finalRef.current = "";
    setFalado("");
    r.onresult = (e) => {
      let interino = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) finalRef.current += `${res[0].transcript} `;
        else interino += res[0].transcript;
      }
      setFalado(finalRef.current);
      setParcial(interino);
    };
    r.onerror = (e) => {
      if (e.error === "not-allowed") toast({ tipo: "erro", titulo: "Microfone bloqueado", descricao: "Libere o acesso ou use um relato pronto." });
    };
    r.onend = () => {
      const dito = finalRef.current.trim();
      if (dito.length >= 3) void enviar(dito);
      else setEstado("parado");
    };
    reconhecimento.current = r;
    setEstado("ouvindo");
    r.start();
  }

  const ocupado = estado === "enviando";
  const IconeOrigem = resultado ? ORIGEM[resultado.origem].icone : null;
  const escutando = estado === "ouvindo" || estado === "gravando";

  return (
    <Secao icone={Radio} titulo="Agente de campo" subtitulo="O voluntário fala, o ponto aparece no mapa">
      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={alternarMicrofone}
          disabled={ocupado}
          aria-pressed={escutando}
          aria-label={escutando ? "Parar e enviar relato" : "Gravar relato por voz"}
          className={`relative grid h-16 w-16 shrink-0 place-items-center rounded-full transition-colors disabled:opacity-60 ${
            escutando ? "bg-ops-vermelho text-white" : "bg-ops-ciano text-ops-bg hover:bg-white"
          }`}
        >
          {escutando && <span className="anel-pulso text-ops-vermelho" aria-hidden />}
          {ocupado ? (
            <LoaderCircle className="h-7 w-7 animate-spin" aria-hidden />
          ) : escutando ? (
            <Square className="h-6 w-6 fill-current" aria-hidden />
          ) : (
            <Mic className="h-7 w-7" aria-hidden />
          )}
        </button>
        <div className="min-w-0 text-sm" aria-live="polite">
          {estado === "parado" && <p className="text-ops-muted">Toque e descreva: local, quantas pessoas, o que falta.</p>}
          {estado === "ouvindo" && (
            <p className="text-ops-texto">
              {falado}
              <span className="text-ops-muted">{parcial || (!falado && "Ouvindo…")}</span>
            </p>
          )}
          {estado === "gravando" && <p className="text-ops-texto">Gravando… toque para enviar.</p>}
          {estado === "enviando" && <p className="text-ops-ciano">Entendendo o relato e localizando no mapa…</p>}
        </div>
      </div>

      <p className="mt-4 text-[11px] font-semibold uppercase tracking-wider text-ops-muted">Relatos prontos</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {relatosProntos.map((r) => (
          <button
            key={r.rotulo}
            title={r.texto}
            disabled={ocupado || escutando}
            onClick={() => void enviar(r.texto)}
            className="rounded-md border border-ops-linha bg-ops-elevado px-2.5 py-1.5 text-xs font-medium text-ops-texto transition-colors hover:border-ops-ciano/60 hover:text-white disabled:opacity-50"
          >
            {r.rotulo}
          </button>
        ))}
      </div>

      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (texto.trim().length >= 3) void enviar(texto.trim());
        }}
      >
        <input
          aria-label="Digitar relato"
          className="min-w-0 flex-1 rounded-md border border-ops-linha bg-ops-bg px-2.5 py-2 text-sm text-ops-texto placeholder:text-ops-muted focus:border-ops-ciano focus:outline-none"
          placeholder="Ou digite o relato…"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
        />
        <button
          type="submit"
          disabled={ocupado || texto.trim().length < 3}
          className="rounded-md bg-ops-elevado px-3 text-sm font-semibold text-ops-texto hover:bg-ops-linha disabled:opacity-40"
        >
          Enviar
        </button>
      </form>

      {resultado && IconeOrigem && (
        <article className="mt-4 animate-fade-up rounded-lg border border-ops-linha bg-ops-bg p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-ops-ciano">
                {resultado.acao === "criado" ? "Novo ponto no mapa" : "Ponto atualizado"}
              </p>
              <p className="truncate font-semibold text-ops-texto">{resultado.ponto.nome}</p>
            </div>
            <Urgencia valor={resultado.extracao.urgencia} />
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-ops-muted">{resultado.extracao.resumo}</p>
          <div className="mt-2.5">
            <ListaItens itens={resultado.extracao.itens} />
          </div>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {resultado.extracao.pessoas !== null && <Etiqueta>{resultado.extracao.pessoas} pessoas</Etiqueta>}
            {resultado.extracao.condicoes.map((c) => (
              <Etiqueta key={c} cor="ambar">
                {ROTULO_CONDICAO[c] ?? c}
              </Etiqueta>
            ))}
            <Etiqueta cor={resultado.geocoding.fonte === "centro" ? "vermelho" : "verde"}>
              <MapPin className="h-3 w-3" aria-hidden />
              {FONTE_GEO[resultado.geocoding.fonte]}
            </Etiqueta>
            <Etiqueta cor={resultado.origem === "fallback" ? "ambar" : resultado.origem === "llm" ? "ciano" : "verde"}>
              <IconeOrigem className="h-3 w-3" aria-hidden />
              {resultado.origem === "llm" ? `IA (${resultado.modelo})` : ORIGEM[resultado.origem].rotulo}
            </Etiqueta>
            {resultado.descartados > 0 && (
              <Etiqueta cor="ambar">{resultado.descartados} item(ns) sem apoio no relato ignorado(s)</Etiqueta>
            )}
            {resultado.pii_removidos > 0 && (
              <Etiqueta cor="verde">
                <ShieldCheck className="h-3 w-3" aria-hidden />
                {resultado.pii_removidos} dado(s) pessoal(is) removido(s)
              </Etiqueta>
            )}
          </div>
          {resultado.aviso && <p className="mt-2 text-xs text-ops-ambar">{resultado.aviso}</p>}
        </article>
      )}
    </Secao>
  );
}
