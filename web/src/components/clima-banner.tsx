"use client";

import { Ellipsis, Snowflake, ThermometerSun } from "lucide-react";

import { Menu, MenuItem } from "@/components/ui/controles";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { useCidade } from "@/lib/cidade";
import type { Clima } from "@/lib/types";

/**
 * Faixa compacta com a previsão. A simulação (frente fria em SP, calor no Rio e em Fortaleza) fica num menu
 * discreto: não é uma ação do usuário comum.
 */
export function ClimaFaixa({ clima, onChange }: { clima: Clima | null; onChange: (c: Clima) => void }) {
  const toast = useToast();
  const { cidade } = useCidade();
  // Frente fria só é plausível em SP; no Rio e em Fortaleza o risco é o calor.
  const frio = cidade.id === "sp";
  if (!clima) return null;

  const temps = clima.regioes.filter((r) => r.temp_min !== null && r.temp_max !== null);
  const min = temps.length ? Math.min(...temps.map((r) => r.temp_min as number)) : null;
  const max = temps.length ? Math.max(...temps.map((r) => r.temp_max as number)) : null;
  const alerta = clima.alertas[0];
  const Icone = alerta?.toLowerCase().includes("frio") ? Snowflake : ThermometerSun;

  async function alternar() {
    try {
      if (clima?.simulacao) {
        onChange(await api.pararSimulacao());
        toast({ tipo: "info", titulo: "De volta à previsão real" });
      } else {
        onChange(frio ? await api.simularClima(6, 14) : await api.simularClima(27, 39));
        toast({
          tipo: "sucesso",
          titulo: frio ? "Frente fria simulada: 6°C" : "Onda de calor simulada: 39°C",
          descricao: frio
            ? "Agasalhos e cobertores subiram de prioridade no mapa."
            : "Água subiu de prioridade no mapa.",
        });
      }
    } catch (e) {
      toast({ tipo: "erro", titulo: "Não deu para mudar o clima", descricao: (e as Error).message });
    }
  }

  return (
    <div
      className={`flex items-start gap-3 rounded-xl border px-3 py-2.5 shadow-float ${
        alerta ? "border-sky-200 bg-sky-50" : "border-line bg-surface"
      }`}
    >
      <Icone className={`mt-0.5 h-5 w-5 shrink-0 ${alerta ? "text-sky-700" : "text-accent"}`} aria-hidden />
      <div className="min-w-0 flex-1 text-sm">
        <p className="font-semibold">
          {min !== null ? `Próximos dias: ${Math.round(min)}° a ${Math.round(max ?? min)}°` : "Previsão indisponível"}
          {clima.simulacao && (
            <span className="ml-2 rounded bg-sky-200 px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-sky-900">
              Simulação
            </span>
          )}
        </p>
        {alerta && <p className="text-muted">{alerta}</p>}
      </div>
      <Menu gatilho={<Ellipsis className="h-4 w-4" aria-hidden />} rotulo="Opções de clima">
        {(fechar) => (
          <MenuItem
            onClick={() => {
              fechar();
              void alternar();
            }}
          >
            {frio ? <Snowflake className="h-4 w-4 text-muted" aria-hidden /> : <ThermometerSun className="h-4 w-4 text-muted" aria-hidden />}
            {clima.simulacao ? "Voltar à previsão real" : frio ? "Simular frente fria (6°C)" : "Simular onda de calor (39°C)"}
          </MenuItem>
        )}
      </Menu>
    </div>
  );
}
