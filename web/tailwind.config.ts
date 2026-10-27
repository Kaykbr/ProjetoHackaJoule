import type { Config } from "tailwindcss";

/**
 * Tokens do Doa Certo, direção "cívico acolhedor".
 * As únicas cores saturadas da interface são as de urgência; o resto é neutro e quente.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#FAF7F2",
        surface: "#FFFFFF",
        sunken: "#F3EEE6",
        line: "#E7E1D6",
        ink: "#1F1D1A",
        muted: "#5E5A52",
        faint: "#8A847A",
        brand: { DEFAULT: "#1F5F5B", dark: "#174845", soft: "#E6EFEC" },
        accent: { DEFAULT: "#C2603A", soft: "#F7E7DF" },
        urg: {
          critica: "#B42318",
          alta: "#C4501C",
          media: "#B7791F",
          baixa: "#667085",
        },
        // Central de operações (tema escuro, painel de cidade inteligente)
        ops: {
          bg: "#0A0F1A",
          painel: "#0F1726",
          elevado: "#152036",
          linha: "#1F2B42",
          texto: "#E5ECF6",
          muted: "#8C9BB5",
          ciano: "#22D3EE",
          verde: "#34D399",
          vermelho: "#F87171",
          laranja: "#FB923C",
          ambar: "#FBBF24",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
      borderRadius: { DEFAULT: "6px", lg: "8px", xl: "12px" },
      boxShadow: {
        float: "0 1px 2px rgb(31 29 26 / 0.06), 0 12px 32px -12px rgb(31 29 26 / 0.22)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulsar: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "fade-up": "fade-up 180ms ease-out both",
        pulsar: "pulsar 1.2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
