"use client";

import {
  ArrowLeft,
  ArrowRight,
  CalendarPlus,
  Check,
  CircleCheck,
  Info,
  MapPin,
  Navigation,
  Plus,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { MapaDinamico } from "@/components/mapa-dinamico";
import { BadgeUrgencia } from "@/components/ui/badge-urgencia";
import { Button, botao } from "@/components/ui/button";
import { Field, Quantidade, Segmented, Stepper } from "@/components/ui/controles";
import { Progresso } from "@/components/ui/progresso";
import { Evidencia, SeloOrigem } from "@/components/ui/selo-origem";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { useCidade } from "@/lib/cidade";
import { capitalizar, km, unidades } from "@/lib/format";
import { agruparPorPonto } from "@/lib/mapa-dados";
import type { Categoria, Doacao, Extracao, ItemOferta, Opcao, Sugestao } from "@/lib/types";

const ETAPAS = ["O que você tem", "Confira", "Onde doar"];
const EXEMPLOS = [
  "Tenho 3 casacos, 2 cobertores e uns 10 sabonetes",
  "Posso doar 20 marmitas e 12 garrafas de água",
  "Tenho meias de lã e um par de tênis 41",
];

type Local = { lat: number; lng: number; rotulo: string };
type Linha = ItemOferta & { estimada: boolean; evidencia: string };

function descricaoItem(item: ItemOferta): string {
  return capitalizar(unidades(item.quantidade, item.item));
}

/** Arquivo .ics de um dia inteiro para lembrar de entregar. */
function baixarLembrete(doacao: Doacao) {
  const amanha = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
  const dia = (doacao.demanda.prazo ?? amanha).replaceAll("-", "");
  const ics = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Doa Certo//PT-BR",
    "BEGIN:VEVENT",
    `UID:doacao-${doacao.id}@doacerto`,
    `DTSTART;VALUE=DATE:${dia}`,
    `SUMMARY:Entregar ${unidades(doacao.quantidade, doacao.demanda.item)} (Doa Certo)`,
    `LOCATION:${doacao.demanda.ponto.nome}\\, ${doacao.demanda.ponto.regiao}`,
    `DESCRIPTION:${doacao.demanda.ponto.ong_nome}. ${doacao.demanda.ponto.referencia}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
  const url = URL.createObjectURL(new Blob([ics], { type: "text/calendar" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `doacao-${doacao.id}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}

function comoEntregar(doacao: Doacao): string {
  const p = doacao.demanda.ponto;
  return p.modo_recebimento === "coleta"
    ? `${p.ong_nome} busca doações na região. Leve até ${p.nome} ou combine a retirada com a ONG.`
    : `Leve até ${p.nome}.${p.referencia ? ` Referência: ${p.referencia}.` : ""}`;
}

export default function DoarPage() {
  const toast = useToast();
  const [etapa, setEtapa] = useState(0);
  const [carregando, setCarregando] = useState<string | null>(null);

  const [texto, setTexto] = useState("");
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [regioes, setRegioes] = useState<Local[]>([]);
  const [modoLocal, setModoLocal] = useState<"bairro" | "gps">("bairro");
  const { cidade } = useCidade();
  const [local, setLocal] = useState<Local>({ lat: cidade.lat, lng: cidade.lng, rotulo: `centro de ${cidade.nome}` });
  const [gpsStatus, setGpsStatus] = useState<string>("");

  const [extracao, setExtracao] = useState<Extracao | null>(null);
  const [linhas, setLinhas] = useState<Linha[]>([]);

  const [sugestoes, setSugestoes] = useState<Sugestao[]>([]);
  const [escolha, setEscolha] = useState<Record<number, number>>({});
  const [foco, setFoco] = useState(0);
  const [apelido, setApelido] = useState("");
  const [feitas, setFeitas] = useState<Record<number, Doacao>>({});

  useEffect(() => {
    api.categorias().then(setCategorias).catch(() => undefined);
    api
      .pontos()
      .then((pontos) => {
        const unicas = new Map<string, Local>();
        pontos.forEach((p) => unicas.has(p.regiao) || unicas.set(p.regiao, { lat: p.lat, lng: p.lng, rotulo: p.regiao }));
        setRegioes([...unicas.values()].sort((a, b) => a.rotulo.localeCompare(b.rotulo)));
      })
      .catch(() => undefined);
  }, []);

  async function executar<T>(etiqueta: string, fn: () => Promise<T>): Promise<T | undefined> {
    setCarregando(etiqueta);
    try {
      return await fn();
    } catch (e) {
      toast({ tipo: "erro", titulo: "Algo deu errado", descricao: (e as Error).message });
      return undefined;
    } finally {
      setCarregando(null);
    }
  }

  function usarGps() {
    setModoLocal("gps");
    if (!navigator.geolocation) return setGpsStatus("Seu navegador não permite localização. Escolha um bairro.");
    setGpsStatus("Buscando sua localização…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        // Arredondado (~1 km): basta para ordenar os pontos, sem guardar a posição exata.
        setLocal({
          lat: Math.round(pos.coords.latitude * 100) / 100,
          lng: Math.round(pos.coords.longitude * 100) / 100,
          rotulo: "Sua localização",
        });
        setGpsStatus("Localização aproximada obtida. Não guardamos esse dado.");
      },
      () => setGpsStatus("Não conseguimos sua localização. Escolha um bairro."),
    );
  }

  async function entender() {
    const r = await executar("extrair", () => api.extrairOferta(texto));
    if (!r) return;
    setExtracao(r);
    setLinhas(
      r.itens.map(({ categoria, item, quantidade, quantidade_estimada, evidencia }) => ({
        categoria,
        item,
        quantidade,
        estimada: quantidade_estimada,
        evidencia,
      })),
    );
    setEtapa(1);
  }

  async function buscar() {
    const itens = linhas.filter((l) => l.item.trim()).map(({ estimada: _e, evidencia: _ev, ...i }) => i);
    const r = await executar("sugerir", () => api.sugestoes(itens, local.lat, local.lng));
    if (!r) return;
    setSugestoes(r);
    setEscolha({});
    setFeitas({});
    setFoco(Math.max(0, r.findIndex((s) => s.opcoes.length > 0)));
    setEtapa(2);
  }

  async function confirmar(i: number, opcao: Opcao) {
    const r = await executar(`doar-${i}`, () =>
      api.prometer(opcao.demanda.id, opcao.quantidade_sugerida, apelido.trim() || "Anônimo"),
    );
    if (!r) return;
    setFeitas((f) => ({ ...f, [i]: r }));
    // Atualiza os números da demanda com o que a API devolveu.
    setSugestoes((lista) =>
      lista.map((s) => ({
        ...s,
        opcoes: s.opcoes.map((o) => (o.demanda.id === r.demanda.id ? { ...o, demanda: r.demanda } : o)),
      })),
    );
    const proximo = sugestoes.findIndex((s, idx) => idx > i && s.opcoes.length > 0 && !feitas[idx]);
    if (proximo >= 0) setFoco(proximo);
  }

  function reiniciar() {
    setEtapa(0);
    setTexto("");
    setExtracao(null);
    setLinhas([]);
    setSugestoes([]);
    setFeitas({});
  }

  const atualizar = (i: number, patch: Partial<Linha>) =>
    setLinhas((l) => l.map((it, idx) => (idx === i ? { ...it, ...patch, estimada: false } : it)));

  const opcaoEscolhida = (i: number): Opcao | undefined => sugestoes[i]?.opcoes[escolha[i] ?? 0];
  const pontosMapa = useMemo(
    () => agruparPorPonto(sugestoes.flatMap((s) => s.opcoes.map((o) => o.demanda))),
    [sugestoes],
  );
  const destino = opcaoEscolhida(foco)?.demanda.ponto;
  const doacoesFeitas = Object.values(feitas);

  // ------------------------------------------------------------------ concluído
  if (etapa === 3) {
    return (
      <div className="container-pg max-w-2xl py-10">
        <span className="grid h-12 w-12 place-items-center rounded-full bg-brand text-white">
          <Check className="h-6 w-6" aria-hidden />
        </span>
        <h1 className="mt-5 text-3xl font-semibold sm:text-4xl">
          {apelido.trim() ? `Obrigado, ${apelido.trim()}.` : "Obrigado."} Sua doação tem destino.
        </h1>
        <p className="mt-2 text-muted">
          A ONG já vê o que está a caminho. Quando ela confirmar o recebimento, isso entra no painel de impacto.
        </p>
        <ul className="mt-8 divide-y divide-line border-y border-line">
          {doacoesFeitas.map((d) => (
            <li key={d.id} className="flex flex-col gap-3 py-5 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="font-semibold">
                  {capitalizar(unidades(d.quantidade, d.demanda.item))} para {d.demanda.ponto.nome}
                </p>
                <p className="mt-1 text-sm text-muted">{comoEntregar(d)}</p>
              </div>
              <Button
                variante="secondary"
                tamanho="sm"
                icone={<CalendarPlus className="h-4 w-4" aria-hidden />}
                onClick={() => baixarLembrete(d)}
              >
                Lembrete na agenda
              </Button>
            </li>
          ))}
        </ul>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button onClick={reiniciar}>Doar mais alguma coisa</Button>
          <Link href="/" className={botao("secondary")}>
            Ver o mapa
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container-pg py-8">
      <header className="max-w-2xl">
        <p className="eyebrow">Quero doar</p>
        <h1 className="mt-2 text-3xl font-semibold sm:text-4xl">Sua doação, onde ela faz falta agora</h1>
        <div className="mt-6">
          <Stepper etapas={ETAPAS} atual={etapa} />
        </div>
      </header>

      {/* ---------------------------------------------------------- etapa 1 */}
      {etapa === 0 && (
        <section className="mt-8 max-w-2xl animate-fade-up space-y-6">
          <Field
            id="oferta"
            label="O que você tem para doar?"
            dica="Escreva do seu jeito. A gente organiza os itens para você conferir."
          >
            <textarea
              id="oferta"
              rows={4}
              className="input resize-none text-base"
              placeholder="Ex.: tenho 3 casacos e uns 10 sabonetes"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
            />
          </Field>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted">Experimente:</span>
            {EXEMPLOS.map((ex) => (
              <button
                key={ex}
                onClick={() => setTexto(ex)}
                className="rounded-md border border-line bg-surface px-2.5 py-1 text-left text-muted hover:border-faint hover:text-ink"
              >
                {ex}
              </button>
            ))}
          </div>

          <fieldset>
            <legend className="mb-1.5 text-sm font-medium">Perto de onde você está?</legend>
            <Segmented
              rotulo="Como informar sua localização"
              valor={modoLocal}
              onChange={(v) => (v === "gps" ? usarGps() : setModoLocal("bairro"))}
              opcoes={[
                { valor: "bairro", rotulo: "Escolher bairro" },
                {
                  valor: "gps",
                  rotulo: (
                    <span className="inline-flex items-center gap-1.5">
                      <Navigation className="h-3.5 w-3.5" aria-hidden />
                      Usar minha localização
                    </span>
                  ),
                },
              ]}
            />
            <div className="mt-3">
              {modoLocal === "bairro" ? (
                <select
                  aria-label="Bairro"
                  className="input max-w-xs"
                  value={local.rotulo}
                  onChange={(e) => {
                    const r = regioes.find((x) => x.rotulo === e.target.value);
                    if (r) setLocal(r);
                  }}
                >
                  {regioes.map((r) => (
                    <option key={r.rotulo}>{r.rotulo}</option>
                  ))}
                </select>
              ) : (
                <p className="flex items-center gap-1.5 text-sm text-muted">
                  <MapPin className="h-4 w-4" aria-hidden />
                  {gpsStatus}
                </p>
              )}
            </div>
          </fieldset>

          <div className="flex justify-end border-t border-line pt-6">
            <Button
              tamanho="lg"
              onClick={entender}
              disabled={texto.trim().length < 3}
              carregando={carregando === "extrair"}
            >
              {carregando === "extrair" ? "Lendo sua mensagem…" : "Continuar"}
              {carregando !== "extrair" && <ArrowRight className="h-4 w-4" aria-hidden />}
            </Button>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------- etapa 2 */}
      {etapa === 1 && extracao && (
        <section className="mt-8 max-w-2xl animate-fade-up">
          <h2 className="text-xl font-semibold">Entendemos assim. Ajuste o que precisar.</h2>
          <div className="mt-2">
            <SeloOrigem origem={extracao.origem} pii={extracao.pii_removidos} descartados={extracao.descartados} />
          </div>
          {extracao.aviso && !linhas.length && <p className="mt-3 text-sm text-urg-media">{extracao.aviso}</p>}

          <ul className="mt-5 divide-y divide-line border-y border-line">
            {linhas.map((l, i) => (
              <li key={i} className="py-4">
                <div className="mb-2">
                  <Evidencia texto={l.evidencia} />
                </div>
                <div className="grid grid-cols-[1fr_auto] gap-3 sm:grid-cols-[170px_1fr_auto_auto] sm:items-center">
                  <select
                    aria-label="Categoria"
                    className="input order-2 sm:order-none"
                    value={l.categoria}
                    onChange={(e) => atualizar(i, { categoria: e.target.value })}
                  >
                    {categorias.map((c) => (
                      <option key={c.slug} value={c.slug}>
                        {c.nome}
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label="Item"
                    className="input order-1 col-span-2 sm:order-none sm:col-span-1"
                    value={l.item}
                    placeholder="Ex.: cobertor"
                    onChange={(e) => atualizar(i, { item: e.target.value })}
                  />
                  <div className="order-3 flex items-center gap-2 sm:order-none">
                    <Quantidade valor={l.quantidade} destaque={l.estimada} onChange={(v) => atualizar(i, { quantidade: v })} />
                  </div>
                  <Button
                    variante="ghost"
                    className="order-4 !px-2 sm:order-none"
                    aria-label={`Remover ${l.item}`}
                    onClick={() => setLinhas((ls) => ls.filter((_, idx) => idx !== i))}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
                {l.estimada && (
                  <p className="mt-2 flex items-center gap-1.5 text-xs text-urg-media">
                    <Info className="h-3.5 w-3.5" aria-hidden />
                    Você não disse quantos. Colocamos {l.quantidade}, confere?
                  </p>
                )}
              </li>
            ))}
          </ul>
          <Button
            variante="ghost"
            tamanho="sm"
            className="mt-2"
            icone={<Plus className="h-4 w-4" aria-hidden />}
            onClick={() => setLinhas((l) => [...l, { categoria: "outros", item: "", quantidade: 1, estimada: false, evidencia: "" }])}
          >
            Adicionar item
          </Button>

          <div className="mt-6 flex justify-between border-t border-line pt-6">
            <Button variante="ghost" icone={<ArrowLeft className="h-4 w-4" aria-hidden />} onClick={() => setEtapa(0)}>
              Voltar
            </Button>
            <Button
              tamanho="lg"
              onClick={buscar}
              disabled={!linhas.some((l) => l.item.trim())}
              carregando={carregando === "sugerir"}
            >
              Ver onde doar
              {carregando !== "sugerir" && <ArrowRight className="h-4 w-4" aria-hidden />}
            </Button>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------- etapa 3 */}
      {etapa === 2 && (
        <section className="mt-8 grid animate-fade-up gap-8 lg:grid-cols-[1fr_380px]">
          <div className="min-w-0 space-y-8">
            <Field id="apelido" label="Como podemos te chamar? (opcional)" dica="A ONG vê só esse apelido.">
              <input
                id="apelido"
                className="input max-w-xs"
                maxLength={60}
                value={apelido}
                placeholder="Anônimo"
                onChange={(e) => setApelido(e.target.value)}
              />
            </Field>

            {sugestoes.map((s, i) => {
              const opcao = opcaoEscolhida(i);
              const feita = feitas[i];
              const outras = s.opcoes.map((o, j) => ({ o, j })).filter(({ j }) => j !== (escolha[i] ?? 0));

              if (!opcao) {
                return (
                  <article key={i} className="panel p-5">
                    <p className="text-sm font-medium text-muted">{descricaoItem(s.item)}</p>
                    <p className="mt-2 font-semibold">Nenhuma ONG pediu isso agora.</p>
                    <p className="mt-1 text-sm text-muted">
                      Guarde para a próxima. Doar o que ninguém pediu costuma virar desperdício.
                    </p>
                  </article>
                );
              }

              const razoes = opcao.razoes.filter((r) => !r.includes("km de você"));
              return (
                <article
                  key={i}
                  onClick={() => setFoco(i)}
                  onFocus={() => setFoco(i)}
                  className={`panel overflow-hidden ${foco === i ? "ring-2 ring-brand/30" : ""}`}
                >
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium text-muted">{descricaoItem(s.item)}</p>
                      <BadgeUrgencia nivel={opcao.demanda.urgencia.nivel} urgencia={opcao.demanda.urgencia} />
                    </div>
                    <h3 className="mt-2 text-2xl font-semibold leading-tight">
                      Leve para {opcao.demanda.ponto.nome}
                    </h3>
                    <p className="mt-1 text-sm text-muted">
                      {opcao.demanda.ponto.ong_nome}, {opcao.demanda.ponto.regiao}. A {km(opcao.distancia_km)} de você.{" "}
                      {opcao.demanda.ponto.modo_recebimento === "coleta" ? "A ONG faz coleta." : "Entrega no ponto."}
                    </p>
                    <ul className="mt-4 space-y-1.5 text-sm">
                      {razoes.map((r) => (
                        <li key={r} className="flex items-start gap-2">
                          <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand" aria-hidden />
                          {capitalizar(r)}
                        </li>
                      ))}
                    </ul>
                    <div className="mt-4">
                      <Progresso demanda={opcao.demanda} />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-sunken/50 px-5 py-3">
                    {feita ? (
                      <p className="flex items-center gap-2 text-sm font-semibold text-brand">
                        <CircleCheck className="h-5 w-5" aria-hidden />
                        Combinado: {unidades(feita.quantidade, feita.demanda.item)} para {feita.demanda.ponto.nome}
                      </p>
                    ) : (
                      <>
                        {outras.length > 0 ? (
                          <details className="text-sm">
                            <summary className="cursor-pointer font-medium text-muted hover:text-ink">
                              Outras opções ({outras.length})
                            </summary>
                            <ul className="mt-2 space-y-1">
                              {outras.map(({ o, j }) => (
                                <li key={o.demanda.id}>
                                  <button
                                    className="text-left hover:underline"
                                    onClick={() => {
                                      setEscolha((e) => ({ ...e, [i]: j }));
                                      setFoco(i);
                                    }}
                                  >
                                    {o.demanda.ponto.nome}, {km(o.distancia_km)}, faltam {o.demanda.faltam}
                                  </button>
                                </li>
                              ))}
                            </ul>
                          </details>
                        ) : (
                          <span />
                        )}
                        <Button onClick={() => confirmar(i, opcao)} carregando={carregando === `doar-${i}`}>
                          Doar {opcao.quantidade_sugerida} aqui
                        </Button>
                      </>
                    )}
                  </div>
                </article>
              );
            })}

            <div className="flex justify-between border-t border-line pt-6">
              <Button variante="ghost" icone={<ArrowLeft className="h-4 w-4" aria-hidden />} onClick={() => setEtapa(1)}>
                Voltar
              </Button>
              <Button tamanho="lg" onClick={() => setEtapa(3)} disabled={!doacoesFeitas.length}>
                Concluir
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Button>
            </div>
          </div>

          <aside className="order-first lg:order-none">
            <div className="h-64 overflow-hidden rounded-xl border border-line lg:sticky lg:top-24 lg:h-[420px]">
              <MapaDinamico
                pontos={pontosMapa}
                doador={local}
                destino={destino ? { lat: destino.lat, lng: destino.lng } : null}
                selecionado={destino?.id ?? null}
              />
            </div>
            <p className="mt-2 text-xs text-muted">Linha reta até o ponto. Não é a rota real.</p>
          </aside>
        </section>
      )}
    </div>
  );
}
