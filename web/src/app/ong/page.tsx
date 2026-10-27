"use client";

import {
  BadgeCheck,
  ArrowRight,
  Check,
  ChevronDown,
  ClipboardList,
  Info,
  Mic,
  PackageCheck,
  Radio,
  Sparkles,
  Trash2,
  Truck,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { BadgeUrgencia } from "@/components/ui/badge-urgencia";
import { Button } from "@/components/ui/button";
import { Field, Menu, MenuItem, Quantidade, Segmented } from "@/components/ui/controles";
import { EmptyState, SkeletonLista } from "@/components/ui/estado";
import { Progresso } from "@/components/ui/progresso";
import { Evidencia, SeloOrigem } from "@/components/ui/selo-origem";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { useCidade } from "@/lib/cidade";
import { capitalizar, plural, prazoTexto, unidades } from "@/lib/format";
import type { Categoria, Demanda, DemandaItemIn, Doacao, Extracao, Ong, Ponto } from "@/lib/types";

const EXEMPLO =
  "Bom dia! Aqui é da equipe da noite. Precisamos urgente de 40 cobertores e uns kits de higiene " +
  "até sexta, e também 30 pares de meia. Qualquer coisa me liga no (11) 98888-7777.";

type Aba = "novo" | "caminho" | "abertos";
type Rascunho = DemandaItemIn & { estimada: boolean; evidencia: string };

// Web Speech API: não faz parte da lib DOM do TypeScript.
interface Reconhecimento {
  lang: string;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onend: (() => void) | null;
}
type ConstrutorReconhecimento = new () => Reconhecimento;

function obterReconhecimento(): ConstrutorReconhecimento | null {
  const w = window as unknown as {
    SpeechRecognition?: ConstrutorReconhecimento;
    webkitSpeechRecognition?: ConstrutorReconhecimento;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function iniciais(nome: string): string {
  return nome
    .split(" ")
    .filter((p) => p.length > 2)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
}

export default function OngPage() {
  const toast = useToast();
  const { cidade } = useCidade();
  const [ongs, setOngs] = useState<Ong[]>([]);
  const [ongId, setOngId] = useState<number | null>(null);
  const [pontos, setPontos] = useState<Ponto[]>([]);
  const [pontoId, setPontoId] = useState<number | null>(null);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [demandas, setDemandas] = useState<Demanda[]>([]);
  const [doacoes, setDoacoes] = useState<Doacao[]>([]);
  const [carregandoDados, setCarregandoDados] = useState(true);
  const [aba, setAba] = useState<Aba>("novo");

  const [texto, setTexto] = useState("");
  const [extracao, setExtracao] = useState<Extracao | null>(null);
  const [rascunho, setRascunho] = useState<Rascunho[]>([]);
  const [ouvindo, setOuvindo] = useState(false);
  const reconhecimento = useRef<Reconhecimento | null>(null);
  const [carregando, setCarregando] = useState<string | null>(null);

  /** Ações com "Desfazer": somem da lista na hora e só vão para a API depois de 5 s. */
  const [ocultos, setOcultos] = useState<Set<string>>(new Set());

  useEffect(() => {
    Promise.all([api.ongs(), api.categorias()])
      .then(([o, c]) => {
        setOngs(o);
        setCategorias(c);
        if (o.length) setOngId(o[0].id);
      })
      .catch((e: Error) => toast({ tipo: "erro", titulo: "Não foi possível carregar", descricao: e.message }));
  }, [toast]);

  const recarregar = useCallback(async () => {
    if (!ongId) return;
    try {
      const [p, d, dc] = await Promise.all([api.pontos(ongId), api.demandas({ ong_id: ongId }), api.doacoes(ongId)]);
      setPontos(p);
      setPontoId((atual) => (atual && p.some((x) => x.id === atual) ? atual : (p[0]?.id ?? null)));
      setDemandas(d);
      setDoacoes(dc);
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não foi possível carregar", descricao: (e as Error).message });
    } finally {
      setCarregandoDados(false);
    }
  }, [ongId, toast]);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  function comDesfazer(chave: string, titulo: string, acao: () => Promise<unknown>) {
    setOcultos((s) => new Set(s).add(chave));
    const mostrar = () =>
      setOcultos((s) => {
        const n = new Set(s);
        n.delete(chave);
        return n;
      });
    const timer = window.setTimeout(async () => {
      try {
        await acao();
        await recarregar();
      } catch (e) {
        toast({ tipo: "erro", titulo: "Não foi possível salvar", descricao: (e as Error).message });
      } finally {
        mostrar();
      }
    }, 5000);
    toast({
      tipo: "sucesso",
      titulo,
      duracao: 5000,
      acao: {
        rotulo: "Desfazer",
        onClick: () => {
          window.clearTimeout(timer);
          mostrar();
        },
      },
    });
  }

  function alternarMicrofone() {
    const Construtor = obterReconhecimento();
    if (!Construtor) {
      toast({ tipo: "erro", titulo: "Ditado indisponível", descricao: "Use o Chrome ou digite o texto." });
      return;
    }
    if (ouvindo) return reconhecimento.current?.stop();
    const r = new Construtor();
    r.lang = "pt-BR";
    r.interimResults = false;
    r.onresult = (e) => {
      const falado = Array.from(e.results)
        .map((res) => res[0].transcript)
        .join(" ");
      setTexto((t) => (t ? `${t} ${falado}` : falado));
    };
    r.onend = () => setOuvindo(false);
    reconhecimento.current = r;
    setOuvindo(true);
    r.start();
  }

  async function interpretar() {
    setCarregando("extrair");
    try {
      const r = await api.extrairDemanda(texto);
      setExtracao(r);
      setRascunho(
        r.itens.map((i) => ({
          categoria: i.categoria,
          item: i.item,
          quantidade: i.quantidade,
          urgencia: i.urgencia,
          prazo: i.prazo,
          estimada: i.quantidade_estimada,
          evidencia: i.evidencia,
        })),
      );
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não conseguimos ler o pedido", descricao: (e as Error).message });
    } finally {
      setCarregando(null);
    }
  }

  async function publicar() {
    if (!pontoId) return;
    setCarregando("publicar");
    try {
      const itens = rascunho.map(({ estimada: _e, evidencia: _ev, ...item }) => item);
      const novas = await api.publicarDemandas(pontoId, itens, extracao ? "ia" : "manual");
      toast({
        tipo: "sucesso",
        titulo: `${plural(novas.length, "pedido publicado", "pedidos publicados")} no mapa`,
        acao: { rotulo: "Ver pedidos", onClick: () => setAba("abertos") },
      });
      setTexto("");
      setExtracao(null);
      setRascunho([]);
      await recarregar();
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não foi possível publicar", descricao: (e as Error).message });
    } finally {
      setCarregando(null);
    }
  }

  const atualizar = (i: number, patch: Partial<DemandaItemIn>) =>
    setRascunho((l) => l.map((it, idx) => (idx === i ? { ...it, ...patch, estimada: false } : it)));

  const ong = ongs.find((o) => o.id === ongId);
  const aCaminho = doacoes.filter((d) => d.status === "prometida" && !ocultos.has(`d${d.id}`));
  const abertas = demandas.filter((d) => !ocultos.has(`p${d.id}`));

  return (
    <div className="container-pg py-8">
      {/* ------------------------------------------------------------ identidade */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-xl bg-brand-soft font-display text-xl font-semibold text-brand-dark">
            {ong ? iniciais(ong.nome) : ""}
          </span>
          <div>
            <p className="eyebrow">Painel da ONG</p>
            <h1 className="mt-1 flex flex-wrap items-center gap-2 text-2xl font-semibold sm:text-3xl">
              {ong?.nome ?? "Carregando…"}
              {ong?.verificada && (
                <span className="inline-flex items-center gap-1 rounded bg-brand-soft px-1.5 py-0.5 font-sans text-xs font-semibold text-brand-dark">
                  <BadgeCheck className="h-3.5 w-3.5" aria-hidden />
                  Verificada
                </span>
              )}
            </h1>
            <p className="mt-0.5 text-sm text-muted">
              {plural(pontos.length, "ponto de atendimento", "pontos de atendimento")} em {ong?.cidade ?? cidade.nome}
            </p>
          </div>
        </div>
        <Menu
          rotulo="Trocar ONG"
          gatilho={
            <>
              Trocar ONG <ChevronDown className="h-4 w-4" aria-hidden />
            </>
          }
        >
          {(fechar) =>
            ongs.map((o) => (
              <MenuItem
                key={o.id}
                onClick={() => {
                  fechar();
                  setCarregandoDados(true);
                  setOngId(o.id);
                }}
              >
                {o.id === ongId ? <Check className="h-4 w-4 text-brand" aria-hidden /> : <span className="w-4" />}
                {o.nome}
              </MenuItem>
            ))
          }
        </Menu>
      </header>

      {/* A central é ferramenta de equipe: fica aqui, não na navegação de quem doa. */}
      <Link
        href="/operacao"
        className="group mt-6 flex items-center gap-4 rounded-xl border border-line bg-surface p-4 transition-colors hover:border-brand/50"
      >
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-ops-bg text-ops-ciano">
          <Radio className="h-5 w-5" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-semibold">Central de operações</span>
          <span className="block text-sm text-muted">
            Relatos de campo por voz, radar de clima e rota de entrega para o motorista em {cidade.nome}.
          </span>
        </span>
        <ArrowRight className="h-5 w-5 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-brand" aria-hidden />
      </Link>

      <div className="mt-8 border-b border-line pb-4">
        <Segmented<Aba>
          rotulo="Seções do painel"
          valor={aba}
          onChange={setAba}
          opcoes={[
            { valor: "novo", rotulo: "Novo pedido" },
            { valor: "caminho", rotulo: `A caminho (${aCaminho.length})` },
            { valor: "abertos", rotulo: `Pedidos abertos (${abertas.length})` },
          ]}
        />
      </div>

      {/* ------------------------------------------------------------ novo pedido */}
      {aba === "novo" && (
        <section className="mt-6 max-w-3xl animate-fade-up space-y-6">
          <Field id="ponto" label="Ponto de atendimento">
            <select id="ponto" className="input max-w-md" value={pontoId ?? ""} onChange={(e) => setPontoId(Number(e.target.value))}>
              {pontos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome}, {p.regiao}
                </option>
              ))}
            </select>
          </Field>

          <Field
            id="texto"
            label="O que está faltando?"
            dica="Escreva ou dite como você mandaria no WhatsApp. A IA organiza e você confere antes de publicar."
          >
            <div className="rounded-lg border border-line bg-surface focus-within:border-brand focus-within:ring-2 focus-within:ring-brand/20">
              <textarea
                id="texto"
                rows={4}
                className="block w-full resize-none rounded-t-lg bg-transparent px-3 py-2.5 text-base placeholder:text-faint focus:outline-none"
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                placeholder="Ex.: precisamos de 40 cobertores e kits de higiene até sexta"
              />
              <div className="flex items-center justify-between border-t border-line px-2 py-1.5">
                <button className="link px-1 text-sm" onClick={() => setTexto(EXEMPLO)}>
                  Usar mensagem de exemplo
                </button>
                <button
                  type="button"
                  onClick={alternarMicrofone}
                  aria-pressed={ouvindo}
                  className={`inline-flex min-h-9 items-center gap-2 rounded-lg px-3 text-sm font-medium ${
                    ouvindo ? "bg-red-50 text-urg-critica" : "text-muted hover:bg-sunken hover:text-ink"
                  }`}
                >
                  {ouvindo ? (
                    <>
                      <span className="h-2.5 w-2.5 animate-pulsar rounded-full bg-urg-critica" aria-hidden />
                      Ouvindo… toque para parar
                    </>
                  ) : (
                    <>
                      <Mic className="h-4 w-4" aria-hidden />
                      Ditar
                    </>
                  )}
                </button>
              </div>
            </div>
          </Field>

          {!extracao && (
            <Button
              tamanho="lg"
              onClick={interpretar}
              disabled={texto.trim().length < 3}
              carregando={carregando === "extrair"}
              icone={<Sparkles className="h-4 w-4" aria-hidden />}
            >
              {carregando === "extrair" ? "Organizando…" : "Organizar pedido"}
            </Button>
          )}

          {extracao && (
            <div className="animate-fade-up space-y-4 border-t border-line pt-6">
              <div>
                <h2 className="text-xl font-semibold">Confira antes de publicar</h2>
                <div className="mt-2">
                  <SeloOrigem origem={extracao.origem} pii={extracao.pii_removidos} descartados={extracao.descartados} />
                </div>
                {extracao.aviso && !rascunho.length && <p className="mt-2 text-sm text-urg-media">{extracao.aviso}</p>}
              </div>

              {rascunho.map((it, i) => (
                <article key={i} className="panel space-y-4 p-4">
                  <Evidencia texto={it.evidencia} />
                  <div className="flex gap-2">
                    <input
                      aria-label="Item"
                      className="input flex-1 font-medium"
                      value={it.item}
                      onChange={(e) => atualizar(i, { item: e.target.value })}
                    />
                    <select
                      aria-label="Categoria"
                      className="input w-36 sm:w-44"
                      value={it.categoria}
                      onChange={(e) => atualizar(i, { categoria: e.target.value })}
                    >
                      {categorias.map((c) => (
                        <option key={c.slug} value={c.slug}>
                          {c.nome}
                        </option>
                      ))}
                    </select>
                    <Button
                      variante="ghost"
                      className="!px-2"
                      aria-label={`Remover ${it.item}`}
                      onClick={() => setRascunho((l) => l.filter((_, idx) => idx !== i))}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden />
                    </Button>
                  </div>
                  <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
                    <div>
                      <p className="mb-1.5 text-xs font-medium text-muted">Quantidade</p>
                      <Quantidade valor={it.quantidade} destaque={it.estimada} onChange={(v) => atualizar(i, { quantidade: v })} />
                    </div>
                    <div>
                      <p className="mb-1.5 text-xs font-medium text-muted">Urgência</p>
                      <Segmented<number>
                        rotulo="Urgência"
                        tamanho="sm"
                        valor={it.urgencia}
                        onChange={(v) => atualizar(i, { urgencia: v })}
                        opcoes={[
                          { valor: 1, rotulo: "Baixa" },
                          { valor: 2, rotulo: "Média" },
                          { valor: 3, rotulo: "Alta" },
                        ]}
                      />
                    </div>
                    <div>
                      <label htmlFor={`prazo-${i}`} className="mb-1.5 block text-xs font-medium text-muted">
                        Prazo
                      </label>
                      <input
                        id={`prazo-${i}`}
                        type="date"
                        className="input w-auto py-2"
                        value={it.prazo ?? ""}
                        onChange={(e) => atualizar(i, { prazo: e.target.value || null })}
                      />
                    </div>
                  </div>
                  {it.estimada && (
                    <p className="flex items-center gap-1.5 text-xs text-urg-media">
                      <Info className="h-3.5 w-3.5" aria-hidden />
                      A mensagem não diz quantos. Colocamos {it.quantidade}, ajuste se precisar.
                    </p>
                  )}
                </article>
              ))}

              <div className="flex flex-wrap items-center gap-3">
                <Button tamanho="lg" onClick={publicar} disabled={!rascunho.length} carregando={carregando === "publicar"}>
                  Publicar {plural(rascunho.length, "pedido")}
                </Button>
                <Button
                  variante="ghost"
                  onClick={() => {
                    setExtracao(null);
                    setRascunho([]);
                  }}
                >
                  Descartar
                </Button>
              </div>
            </div>
          )}
        </section>
      )}

      {/* ------------------------------------------------------------ a caminho */}
      {aba === "caminho" && (
        <section className="mt-6 max-w-3xl animate-fade-up">
          {carregandoDados ? (
            <SkeletonLista linhas={3} />
          ) : aCaminho.length === 0 ? (
            <EmptyState
              icone={Truck}
              titulo="Nenhuma doação a caminho"
              texto="Quando alguém escolher doar para um dos seus pedidos, aparece aqui."
            />
          ) : (
            <ul className="divide-y divide-line border-y border-line">
              {aCaminho.map((d) => (
                <li key={d.id} className="flex flex-wrap items-center justify-between gap-3 py-4">
                  <div>
                    <p className="font-semibold">
                      {capitalizar(unidades(d.quantidade, d.demanda.item))}
                    </p>
                    <p className="text-sm text-muted">
                      De {d.doador_apelido} para {d.demanda.ponto.nome}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      tamanho="sm"
                      icone={<PackageCheck className="h-4 w-4" aria-hidden />}
                      onClick={() =>
                        comDesfazer(`d${d.id}`, `Recebimento de ${unidades(d.quantidade, d.demanda.item)} registrado`, () =>
                          api.alterarDoacao(d.id, "entregue"),
                        )
                      }
                    >
                      Recebi
                    </Button>
                    <Button
                      tamanho="sm"
                      variante="secondary"
                      onClick={() =>
                        comDesfazer(`d${d.id}`, "Doação marcada como não entregue", () => api.alterarDoacao(d.id, "cancelada"))
                      }
                    >
                      Não veio
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* ------------------------------------------------------------ abertos */}
      {aba === "abertos" && (
        <section className="mt-6 animate-fade-up">
          {carregandoDados ? (
            <SkeletonLista />
          ) : abertas.length === 0 ? (
            <EmptyState
              icone={ClipboardList}
              titulo="Nenhum pedido aberto"
              texto="Publique o que está faltando na aba Novo pedido."
              acao={<Button onClick={() => setAba("novo")}>Criar pedido</Button>}
            />
          ) : (
            <ul className="divide-y divide-line border-y border-line">
              {abertas.map((d) => (
                <li key={d.id} className="grid gap-3 py-4 sm:grid-cols-[1fr_220px_auto] sm:items-center sm:gap-6">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-semibold">{capitalizar(d.item)}</p>
                      <BadgeUrgencia nivel={d.urgencia.nivel} urgencia={d.urgencia} />
                    </div>
                    <p className="mt-0.5 text-sm text-muted">
                      {d.ponto.nome}. {prazoTexto(d.prazo)}.
                      {d.origem === "ia" && " Criado com IA e revisado."}
                    </p>
                  </div>
                  <Progresso demanda={d} />
                  <Button
                    tamanho="sm"
                    variante="ghost"
                    onClick={() =>
                      comDesfazer(`p${d.id}`, `Pedido de ${d.item} encerrado`, () => api.alterarDemanda(d.id, "atendida"))
                    }
                  >
                    Encerrar
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
