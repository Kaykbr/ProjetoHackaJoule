"""Configuração da aplicação, lida de variáveis de ambiente / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

#: Valores do .env.example que não contam como chave real de LLM.
PLACEHOLDER_KEYS = {"", "coloque_sua_chave_aqui", "changeme", "your_api_key_here"}

#: api/.env, independente da pasta de onde o uvicorn foi iniciado.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    app_name: str = "Doa Certo API"
    environment: str = "development"

    # Persistência: SQLite por padrão (zero setup); Postgres via DATABASE_URL.
    database_url: str = "sqlite:///./doacerto.db"

    # CORS (lista separada por vírgula)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Camada de IA. Gemini usa LLM_API_KEY ou GEMINI_API_KEY; OpenAI usa OPENAI_API_KEY.
    # Sem nenhuma chave, tudo roda com regras locais (a demo nunca quebra).
    llm_provider: str = "gemini"
    llm_model_name: str = "gemini-3.5-flash-lite"
    llm_api_key: str = ""
    gemini_api_key: str = ""
    llm_api_url: str = "https://generativelanguage.googleapis.com/v1beta"
    openai_api_key: str = ""
    openai_api_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20.0
    #: Teto de chamadas ao LLM por dia (protege a chave no site público). Acima disso: regras locais.
    llm_max_chamadas_dia: int = 300
    #: Limite por IP nas rotas que usam IA (requisições por minuto).
    limite_ia_por_minuto: int = 20
    #: Com valor, /ops/reset exige o cabeçalho X-Admin-Token (use no site público).
    admin_token: str = ""
    #: Regras locais resolvem a mensagem simples; o LLM só recebe a ambígua.
    cascata_enabled: bool = True
    #: Mesma mensagem no mesmo dia reaproveita o resultado já validado.
    cache_ia_enabled: bool = True
    #: Preço de referência (USD por 1M tokens) para estimar custo no painel de impacto.
    #: No plano gratuito o custo real é zero; o número mostra quanto custaria em produção.
    llm_preco_entrada_por_milhao: float = 0.10
    llm_preco_saida_por_milhao: float = 0.40

    # Clima (Open-Meteo: gratuito, sem chave)
    clima_enabled: bool = True
    clima_api_url: str = "https://api.open-meteo.com/v1/forecast"
    clima_cache_minutos: int = 30
    clima_dias_previsao: int = 3

    # Regras de urgência (deterministicas, explicáveis)
    frio_limite_c: float = 13.0
    frio_extremo_c: float = 8.0
    calor_limite_c: float = 30.0

    # Matching doador → demanda
    raio_busca_km: float = 15.0
    peso_urgencia: float = 0.6
    peso_proximidade: float = 0.4

    # Central de operações (Fase 2): geocoding e rotas. Dados por cidade ficam em app/cidades.py.
    nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    nominatim_enabled: bool = True
    osrm_url: str = "https://router.project-osrm.org/route/v1/driving"
    osrm_enabled: bool = True
    http_user_agent: str = "DoaCerto-POC/0.2 (hackathon; demo sem fins comerciais)"
    #: Raio para considerar que um relato novo é do mesmo ponto já mapeado.
    raio_mesmo_ponto_km: float = 0.35

    # Otimizador de rotas
    capacidade_veiculo_itens: int = 400
    max_entregas_rota: int = 4
    #: Ruas não são linha reta: multiplica a distância em linha reta quando o OSRM falha.
    fator_desvio_ruas: float = 1.3
    velocidade_media_kmh: float = 22.0
    #: kg CO2 por km. Carro particular (ida e volta de cada doador) × utilitário leve da ONG
    #: (tipo Fiorino) fazendo uma rota única com retorno à base.
    fator_co2_carro_kg_km: float = 0.192
    fator_co2_van_kg_km: float = 0.21

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def chave(self, provider: str) -> str:
        """Chave real do provider, ou "" se ausente/placeholder."""
        if provider == "gemini":
            valor = self.llm_api_key or self.gemini_api_key
        elif provider == "openai":
            valor = self.openai_api_key or (
                self.llm_api_key if self.llm_provider.lower() == "openai" else ""
            )
        else:
            valor = ""
        valor = valor.strip()
        return "" if valor.lower() in PLACEHOLDER_KEYS else valor

    @property
    def provider_efetivo(self) -> str:
        """gemini | openai | offline, conforme LLM_PROVIDER e as chaves disponíveis."""
        pedido = self.llm_provider.lower()
        if pedido == "offline":
            return "offline"
        if pedido == "openai":
            return "openai" if self.chave("openai") else "offline"
        if self.chave("gemini"):
            return "gemini"
        if self.chave("openai"):
            return "openai"
        return "offline"

    @property
    def modelo_efetivo(self) -> str:
        return {"gemini": self.llm_model_name, "openai": self.openai_model}.get(
            self.provider_efetivo, "regras-locais"
        )

    @property
    def llm_enabled(self) -> bool:
        """A IA remota só é considerada disponível quando há uma chave real configurada."""
        return self.provider_efetivo != "offline"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
