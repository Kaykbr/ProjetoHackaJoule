/**
 * Cliente HTTP único da aplicação. Nenhum componente deve chamar `fetch` diretamente.
 * Erros da API viram `ApiError` com a mensagem pronta para exibir.
 */
import type {
  Categoria,
  CidadeDetalhe,
  Clima,
  Demanda,
  DemandaItemIn,
  Doacao,
  Extracao,
  Impacto,
  ItemOferta,
  Ong,
  Ponto,
  Sugestao,
} from "@/lib/types";
import type {
  Cenario,
  EstadoOps,
  ModoRota,
  PontoDemanda,
  Radar,
  RelatoResultado,
  RotaOtimizada,
} from "@/lib/types-ops";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Cidade ativa, definida pelo `CidadeProvider`: vai em toda chamada como `?cidade=`. */
let cidadeAtual = "sp";

export function definirCidadeApi(cidade: string): void {
  cidadeAtual = cidade;
}

function comCidade(path: string): string {
  return `${path}${path.includes("?") ? "&" : "?"}cidade=${cidadeAtual}`;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    // FormData (upload de áudio) define o próprio Content-Type com o boundary.
    const json = !(init?.body instanceof FormData);
    response = await fetch(`${BASE_URL}${comCidade(path)}`, {
      ...init,
      headers: { ...(json ? { "Content-Type": "application/json" } : {}), ...init?.headers },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("Sem conexão com o servidor. Confira a internet e tente de novo.", 0);
  }
  if (!response.ok) {
    let detail = `Erro ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* corpo não-JSON: mantém a mensagem genérica */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

const post = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });
const patch = <T>(path: string, body: unknown) =>
  request<T>(path, { method: "PATCH", body: JSON.stringify(body) });

function query(params: Record<string, string | number | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
}

export const api = {
  cidades: () => request<CidadeDetalhe[]>("/cidades"),
  categorias: () => request<Categoria[]>("/categorias"),
  ongs: () => request<Ong[]>("/ongs"),
  pontos: (ongId?: number) => request<Ponto[]>(`/pontos${query({ ong_id: ongId })}`),

  demandas: (params: { status?: string; categoria?: string; ong_id?: number } = {}) =>
    request<Demanda[]>(`/demandas${query(params)}`),
  extrairDemanda: (texto: string) => post<Extracao>("/demandas/extrair", { texto }),
  publicarDemandas: (ponto_id: number, itens: DemandaItemIn[], origem: "ia" | "manual") =>
    post<Demanda[]>("/demandas", { ponto_id, itens, origem }),
  alterarDemanda: (id: number, status: Demanda["status"]) =>
    patch<Demanda>(`/demandas/${id}`, { status }),

  extrairOferta: (texto: string) => post<Extracao>("/ofertas/extrair", { texto }),
  sugestoes: (itens: ItemOferta[], lat: number, lng: number) =>
    post<Sugestao[]>("/ofertas/sugestoes", { itens, lat, lng }),

  doacoes: (ongId?: number) => request<Doacao[]>(`/doacoes${query({ ong_id: ongId })}`),
  prometer: (demanda_id: number, quantidade: number, doador_apelido: string) =>
    post<Doacao>("/doacoes", { demanda_id, quantidade, doador_apelido }),
  alterarDoacao: (id: number, status: "entregue" | "cancelada") =>
    patch<Doacao>(`/doacoes/${id}`, { status }),

  clima: () => request<Clima>("/clima"),
  simularClima: (temp_min: number, temp_max = 15) =>
    post<Clima>("/clima/simulacao", { temp_min, temp_max }),
  pararSimulacao: () => request<Clima>("/clima/simulacao", { method: "DELETE" }),

  impacto: () => request<Impacto>("/impacto"),
};

/** Central de operações (Fase 2). */
export const ops = {
  estado: () => request<EstadoOps>("/ops/estado"),
  relato: (texto: string) => post<RelatoResultado>("/ops/relatos", { texto }),
  relatoAudio: (audio: Blob) => {
    const form = new FormData();
    const extensao = audio.type.includes("ogg") ? "ogg" : audio.type.includes("mp4") ? "m4a" : "webm";
    form.append("arquivo", audio, `relato.${extensao}`);
    return request<RelatoResultado>("/ops/relatos/audio", { method: "POST", body: form });
  },
  radar: (cenario: Cenario) => request<Radar>(`/ops/radar${query({ cenario })}`),
  gerarRota: (modo: ModoRota, cenario: Cenario, max_entregas: number) =>
    post<RotaOtimizada>("/ops/rotas", { modo, cenario, max_entregas }),
  concluirRota: (id: number) => post<RotaOtimizada>(`/ops/rotas/${id}/concluir`, {}),
  moverPonto: (id: number, lat: number, lng: number) =>
    patch<PontoDemanda>(`/ops/pontos/${id}`, { lat, lng }),
  reset: (tokenAdmin: string) =>
    request<EstadoOps>("/ops/reset", { method: "POST", headers: { "X-Admin-Token": tokenAdmin } }),
};
