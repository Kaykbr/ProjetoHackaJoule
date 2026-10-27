import type { Metadata } from "next";

import { Rodape } from "@/components/nav";

export const metadata: Metadata = { title: "Impacto" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Rodape />
    </>
  );
}
