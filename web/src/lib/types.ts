/** Espelho dos schemas Pydantic da API (app/schemas/__init__.py). */

export type Nivel = "baixa" | "media" | "alta" | "critica";

export interface Categoria {
  slug: string;
  nome: string;
  sensivel_frio: boolean;
  sensivel_calor: boolean;
}

export interface Ong {
  id: number;
  nome: string;
  descricao: string;
  cidade: string;
  contato_publico: string;
  verificada: boolean;
}

export interface Ponto {
  id: number;
  ong_id: number;
  ong_nome: string;
  nome: string;
  regiao: string;
  lat: number;
  lng: number;
  referencia: string;
  modo_recebimento: "entrega" | "coleta";
}

export interface Urgencia {
  score: number;
  nivel: Nivel;
  razoes: string[];
}

export interface Demanda {
  id: number;
  ponto: Ponto;
  categoria: string;
  categoria_nome: string;
  item: string;
  quantidade: number;
  quantidade_prometida: number;
  quantidade_recebida: number;
  faltam: number;
  urgencia_base: number;
  prazo: string | null;
  status: "aberta" | "atendida" | "cancelada";
  origem: "ia" | "manual";
  urgencia: Urgencia;
  created_at: string;
}

export interface ItemExtraido {
  categoria: string;
  categoria_nome: string;
  item: string;
  quantidade: number;
  quantidade_estimada: boolean;
  urgencia: number;
  prazo: string | null;
  /** Trecho da mensagem que justifica o item (conferido no backend). */
  evidencia: string;
}

/** llm = IA remota · regras = texto simples, resolvido sem IA · cache · fallback = IA indisponível. */
export type OrigemIA = "llm" | "regras" | "cache" | "fallback";

export interface Extracao {
  itens: ItemExtraido[];
  fonte: string;
  modelo: string;
  offline: boolean;
  origem: OrigemIA;
  pii_removidos: number;
  /** Itens devolvidos pelo modelo sem apoio no texto, descartados antes de chegar aqui. */
  descartados: number;
  aviso: string;
}

export interface ItemOferta {
  categoria: string;
  item: string;
  quantidade: number;
}

export interface DemandaItemIn extends ItemOferta {
  urgencia: number;
  prazo: string | null;
}

export interface Opcao {
  demanda: Demanda;
  distancia_km: number;
  score: number;
  quantidade_sugerida: number;
  razoes: string[];
}

export interface Sugestao {
  item: ItemOferta;
  opcoes: Opcao[];
}

export interface Doacao {
  id: number;
  demanda: Demanda;
  quantidade: number;
  doador_apelido: string;
  status: "prometida" | "entregue" | "cancelada";
  created_at: string;
}

export interface ClimaRegiao {
  regiao: string;
  temp_min: number | null;
  temp_max: number | null;
  fonte: string;
}

export interface Clima {
  simulacao: boolean;
  regioes: ClimaRegiao[];
  alertas: string[];
}

export interface Impacto {
  ongs: number;
  pontos: number;
  demandas_abertas: number;
  demandas_atendidas: number;
  itens_prometidos: number;
  itens_entregues: number;
  doacoes: number;
  ia: {
    llm_ativo: boolean;
    provider: string;
    modelo: string;
    chamadas: number;
    chamadas_offline: number;
    chamadas_llm: number;
    resolvidas_regras: number;
    cache_hits: number;
    fallback: number;
    itens_sem_evidencia: number;
    tokens: number;
    custo_estimado_usd: number;
    custo_medio_usd: number;
    pii_removidos: number;
  };
}

/** `GET /cidades`: cenários de clima plausíveis e relatos de exemplo de cada cidade. */
export interface CidadeDetalhe {
  id: string;
  nome: string;
  uf: string;
  lat: number;
  lng: number;
  cenarios: { id: string; rotulo: string }[];
  relatos_exemplo: { rotulo: string; texto: string }[];
}
