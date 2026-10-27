import type { NextConfig } from "next";

/**
 * Publicação: o site chama `/api/...` na própria origem e o Next repassa para a API.
 * Assim só o site fica exposto e não há CORS. `API_INTERNA_URL` é lido no build:
 * - na Vercel, é o endereço da API no Render (variável do projeto na Vercel);
 * - no PC com Tailscale, é a API local (ver `scripts/servir.ps1`).
 */
const API_INTERNA = process.env.API_INTERNA_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Build de produção em pasta própria: não atrapalha o `next dev` rodando ao lado.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // ...e com tsconfig próprio: os tipos gerados de cada pasta não se misturam no `npm run typecheck`.
  typescript: { tsconfigPath: process.env.NEXT_DIST_DIR ? "tsconfig.prod.json" : "tsconfig.json" },
  poweredByHeader: false,
  // Na Vercel (VERCEL=1 no build) o navegador sempre fala com `/api` da própria origem.
  env: process.env.VERCEL && !process.env.NEXT_PUBLIC_API_URL ? { NEXT_PUBLIC_API_URL: "/api" } : {},
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_INTERNA}/:path*` }];
  },
};

export default nextConfig;
