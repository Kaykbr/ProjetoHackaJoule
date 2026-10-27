/** Espelho dos schemas da central de operações (api/app/schemas/ops.py). */

import type { OrigemIA } from "@/lib/types";

export type CategoriaOps = "alimentacao" | "agasalho" | "higiene" | "saude";
export type Cenario = "normal" | "frente_fria" | "tempestade" | "onda_de_calor";
export type ModoRota = "atual" | "preditivo";
export type NivelRisco = "baixo" | "moderado" | "alto" | "critico";

export interface ItemOps {
  categoria: CategoriaOps;
  item: string;
  quantidade: number;
}

export interface BaseOps {
  id: number;
  nome: string;
  endereco: string;
  lat: number;
  lng: number;
}

export interface PontoDemanda {
  id: number;
  nome: string;
  bairro: string;
  lat: number;
  lng: number;
  pessoas: number;
  urgencia: number;
  resumo: string;
  itens: ItemOps[];
  condicoes: string[];
  origem: string;
  relatos_30d: number;
  status: string;
  transcricao: string;
  atualizado_em: string;
  total_itens: number;
}

export interface Doador {
  id: number;
  nome: string;
  tipo: string;
  endereco: string;
  lat: number;
  lng: number;
  estoque: ItemOps[];
  total_itens: number;
}

export interface KpisOps {
  pessoas_assistidas: number;
  match_doacoes_pct: number;
  kg_desperdicio_evitado: number;
  co2_economizado_kg: number;
  demandas_abertas: number;
  rotas_concluidas: number;
}

export interface EstadoOps {
  base: BaseOps;
  demandas: PontoDemanda[];
  doadores: Doador[];
  kpis: KpisOps;
  llm_ativo: boolean;
}

export interface ItemRelato extends ItemOps {
  /** Trecho do relato que justifica o item (conferido no backend). */
  evidencia: string;
}

export interface RelatoExtraido {
  local_referencia: string;
  bairro: string;
  pessoas: number | null;
  itens: ItemRelato[];
  urgencia: number;
  resumo: string;
  condicoes: string[];
  transcricao: string;
}

export interface RelatoResultado {
  acao: "criado" | "atualizado";
  ponto: PontoDemanda;
  extracao: RelatoExtraido;
  geocoding: { fonte: "dicionario" | "nominatim" | "centro"; consulta: string; lat: number; lng: number };
  fonte: string;
  modelo: string;
  offline: boolean;
  origem: OrigemIA;
  pii_removidos: number;
  descartados: number;
  aviso: string;
}

export interface HoraPrevisao {
  hora: string;
  temp: number;
  chuva_prob: number;
  vento_kmh: number;
}

export interface Previsao {
  fonte: "open-meteo" | "simulacao" | "padrao";
  cenario: Cenario;
  temp_agora: number;
  temp_min_24h: number;
  temp_max_24h: number;
  chuva_prob_max: number;
  chuva_mm_24h: number;
  vento_max_kmh: number;
  serie: HoraPrevisao[];
}

export interface RiscoPonto {
  ponto_id: number;
  risco_atual: number;
  risco_24h: number;
  nivel: NivelRisco;
  fatores: string[];
  demanda_projetada: ItemOps[];
}

export interface AlertaPreditivo {
  id: string;
  severidade: "info" | "atencao" | "critico";
  titulo: string;
  descricao: string;
  categoria: CategoriaOps | null;
  aumento_pct: number | null;
  pontos: number[];
}

export interface Radar {
  cenario: Cenario;
  previsao: Previsao;
  indice_clima: number;
  riscos: RiscoPonto[];
  alertas: AlertaPreditivo[];
  aumento_projetado: Record<CategoriaOps, number>;
}

export interface Parada {
  ordem: number;
  tipo: "base" | "coleta" | "entrega" | "retorno";
  ref_id: number;
  nome: string;
  lat: number;
  lng: number;
  itens: ItemOps[];
  distancia_desde_anterior_km: number;
  chegada_min: number;
}

export interface RotaOtimizada {
  id: number;
  modo: ModoRota;
  cenario: Cenario;
  status: "planejada" | "concluida";
  fonte_rota: "osrm" | "estimativa";
  paradas: Parada[];
  geometria: [number, number][];
  distancia_km: number;
  tempo_min: number;
  taxa_atendimento_pct: number;
  itens_entregues: number;
  kg_entregues: number;
  pessoas_atendidas: number;
  co2_rota_kg: number;
  co2_baseline_kg: number;
  co2_evitado_kg: number;
  viagens_evitadas: number;
  nao_atendido: { ponto_id: number; nome: string; itens: ItemOps[] }[];
  criada_em: string;
}
