import type { Metadata, Viewport } from "next";
import { Fraunces, Public_Sans } from "next/font/google";
import { cookies } from "next/headers";

import { Nav, NavInferior } from "@/components/nav";
import { ToastProvider } from "@/components/ui/toast";
import { CidadeProvider } from "@/lib/cidade";
import { COOKIE_CIDADE, cidadeValida } from "@/lib/cidades";

import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  axes: ["opsz", "SOFT"],
  display: "swap",
});

const publicSans = Public_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Doa Certo", template: "%s | Doa Certo" },
  description:
    "Conecta doadores a pedidos reais de ONGs que atendem pessoas em situação de rua. A doação certa, no lugar certo.",
};

export const viewport: Viewport = { themeColor: "#FAF7F2" };

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cidade = cidadeValida((await cookies()).get(COOKIE_CIDADE)?.value) ?? "sp";
  return (
    <html lang="pt-BR" className={`${fraunces.variable} ${publicSans.variable}`}>
      <body className="flex min-h-dvh flex-col">
        <ToastProvider>
          <CidadeProvider inicial={cidade}>
            <Nav />
            <main className="flex flex-1 flex-col pb-16 md:pb-0">{children}</main>
            <NavInferior />
          </CidadeProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
