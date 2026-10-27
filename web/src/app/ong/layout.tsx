import type { Metadata } from "next";

import { Rodape } from "@/components/nav";

export const metadata: Metadata = { title: "Painel da ONG" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Rodape />
    </>
  );
}
