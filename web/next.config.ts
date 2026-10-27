import type { NextConfig } from "next";

/**
 * Publicação: o site chama `/api/...` na própria origem e o Next repassa para a API local.
 * Assim só uma porta fica exposta (o Tailscale Funnel aponta para o site) e não há CORS.
 * `API_INTERNA_URL` e `NEXT_DIST_DIR` são lidos no build (ver `scripts/servir.ps1`).
 */
const API_INTERNA = process.env.API_INTERNA_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Build de produção em pasta própria: não atrapalha o `next dev` rodando ao lado.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // ...e com tsconfig próprio: os tipos gerados de cada pasta não se misturam no `npm run typecheck`.
  typescript: { tsconfigPath: process.env.NEXT_DIST_DIR ? "tsconfig.prod.json" : "tsconfig.json" },
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_INTERNA}/:path*` }];
  },
};

export default nextConfig;
