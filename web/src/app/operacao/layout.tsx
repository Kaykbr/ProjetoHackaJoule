import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Central de operações",
  description: "Agente de campo por voz, radar preditivo de clima e rotas inteligentes de coleta e entrega.",
};

export const viewport: Viewport = { themeColor: "#0A0F1A" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
