"""docs/SOLUCAO.md -> HTML estilizado -> docs/SOLUCAO.pdf (Chrome sem interface).

Uso: python scripts/gerar_pdf_solucao.py   (precisa do pacote `markdown` e do Google Chrome)
"""
import pathlib
import re
import subprocess
import tempfile

import markdown
from markdown.extensions.toc import slugify_unicode

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MD = RAIZ / "docs" / "SOLUCAO.md"
HTML = pathlib.Path(tempfile.gettempdir()) / "doacerto_solucao.html"
PDF = RAIZ / "docs" / "SOLUCAO.pdf"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

texto = MD.read_text(encoding="utf-8")

# Capa própria: tira o título, o slogan e o aviso do topo do Markdown.
inicio_sumario = texto.index("## Sumário")
texto = texto[inicio_sumario:]
# Links relativos para os outros .md não funcionam no PDF: viram texto simples.
texto = re.sub(r"\[([^\]]+)\]\((?:\.\./README\.md|PITCH\.md)\)", r"**\1**", texto)

corpo = markdown.markdown(
    texto,
    extensions=["tables", "fenced_code", "toc", "sane_lists"],
    extension_configs={"toc": {"slugify": slugify_unicode}},
)

CSS = """
@page {
  size: A4;
  margin: 18mm 17mm 20mm 17mm;
  @bottom-left { content: "Doa Certo · a solução completa"; font: 8pt 'Segoe UI', sans-serif; color: #8a8278; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt 'Segoe UI', sans-serif; color: #8a8278; }
}
@page :first { margin: 0; @bottom-left { content: none; } @bottom-right { content: none; } }

:root {
  --tinta: #1f1c19; --suave: #5f5850; --linha: #e4ddd3; --fundo: #faf7f2;
  --marca: #1f6b5c; --marca-escura: #164f44; --marca-clara: #e3f0ec; --acento: #c2612f;
}
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 10pt; line-height: 1.55;
       color: var(--tinta); margin: 0; }

/* ---------------------------------------------------------------- capa */
.capa { height: 297mm; padding: 34mm 22mm 24mm; display: flex; flex-direction: column;
        background: var(--fundo); break-after: page; position: relative; overflow: hidden; }
.capa::before { content: ""; position: absolute; right: -60mm; top: -60mm; width: 170mm; height: 170mm;
                border-radius: 50%; background: var(--marca-clara); }
.capa::after { content: ""; position: absolute; right: 18mm; top: 52mm; width: 46mm; height: 46mm;
               border-radius: 50%; background: var(--acento); opacity: .9; }
.capa * { position: relative; z-index: 1; }
.selo { display: inline-block; font-size: 8.5pt; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
        color: var(--marca); }
.capa h1 { font-family: Georgia, 'Times New Roman', serif; font-size: 46pt; line-height: 1.02; margin: 10mm 0 0;
           color: var(--tinta); font-weight: 700; letter-spacing: -.01em; }
.capa .subtitulo { font-family: Georgia, serif; font-size: 17pt; color: var(--marca-escura); margin: 6mm 0 0; max-width: 125mm; }
.capa .descricao { font-size: 11pt; color: var(--suave); margin-top: 10mm; max-width: 112mm; }
.capa .rodape { margin-top: auto; border-top: 1px solid var(--linha); padding-top: 6mm; display: grid;
                grid-template-columns: repeat(3, 1fr); gap: 6mm; font-size: 8.5pt; color: var(--suave); }
.capa .rodape strong { display: block; color: var(--tinta); font-size: 9.5pt; margin-bottom: 1mm; }
.capa .aviso { margin-top: 8mm; font-size: 8.5pt; color: var(--suave); background: #fff; border: 1px solid var(--linha);
               border-radius: 3mm; padding: 3.5mm 4.5mm; max-width: 140mm; }

/* ---------------------------------------------------------------- texto */
h2 { font-family: Georgia, serif; font-size: 19pt; line-height: 1.2; margin: 0 0 4mm; color: var(--tinta);
     padding-bottom: 2.5mm; border-bottom: 2px solid var(--marca); break-after: avoid; margin-top: 11mm; }
h2#sumário { border-bottom-color: var(--acento); margin-top: 0; }
/* Capítulos grandes começam em página nova. */
h2[id="6-o-uso-da-ia"], h2[id="8-arquitetura-técnica"], h2[id="11-avaliação-honesta-dá-para-pódio"] { break-before: page; margin-top: 0; }
h3 { font-size: 12pt; margin: 7mm 0 2mm; color: var(--marca-escura); break-after: avoid; }
p { margin: 0 0 3mm; }
strong { color: #000; }
a { color: var(--marca); text-decoration: none; }
ul, ol { margin: 0 0 3.5mm; padding-left: 6mm; }
li { margin-bottom: 1.2mm; }
li > ul, li > ol { margin-top: 1.2mm; }
hr { display: none; }
em { color: var(--suave); }

blockquote { margin: 3mm 0 4mm; padding: 3mm 4.5mm; background: #fdf3ec; border-left: 3px solid var(--acento);
             border-radius: 0 2mm 2mm 0; color: var(--suave); break-inside: avoid; }
blockquote p { margin: 0; }

table { width: 100%; border-collapse: collapse; margin: 2mm 0 5mm; font-size: 8.8pt; break-inside: avoid; }
thead th { background: var(--marca); color: #fff; text-align: left; font-weight: 600; padding: 2mm 2.5mm; }
thead th:first-child { border-top-left-radius: 1.5mm; } thead th:last-child { border-top-right-radius: 1.5mm; }
td { padding: 1.8mm 2.5mm; border-bottom: 1px solid var(--linha); vertical-align: top; }
tbody tr:nth-child(even) td { background: #fbf9f5; }
tbody tr:last-child td { border-bottom: 2px solid var(--marca); }
td strong { color: var(--marca-escura); }
td:nth-child(2) strong { white-space: nowrap; }

code { font-family: 'Cascadia Mono', Consolas, monospace; font-size: 8.4pt; background: #f1ece4;
       padding: .3mm 1.2mm; border-radius: 1mm; }
pre { background: #1d2a27; color: #e8efe9; border-radius: 2.5mm; padding: 4mm 4.5mm; margin: 2mm 0 5mm;
      font-size: 7pt; line-height: 1.38; overflow: hidden; white-space: pre; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; color: inherit; }

/* Sumário em duas colunas */
h2#sumário + ol { columns: 2; column-gap: 10mm; font-size: 10.5pt; }
h2#sumário + ol li { break-inside: avoid; }
"""

CAPA = """
<section class="capa">
  <span class="selo">Hackathon · documento da solução</span>
  <h1>Doa Certo</h1>
  <p class="subtitulo">A doação certa, no lugar certo, na hora certa.</p>
  <p class="descricao">Conecta doadores a pedidos reais de ONGs que atendem pessoas em situação de rua,
  com uma central de operações que transforma relatos de campo em pontos no mapa, antecipa o efeito
  do clima em 24 horas e monta a rota de coleta e entrega.</p>
  <p class="aviso">Protótipo feito por uma pessoa em 2 dias. ONGs, doadores e relatos de demonstração são
  fictícios; os lugares públicos e o clima são reais.</p>
  <div class="rodape">
    <div><strong>Link público</strong>doacerto.tailc7bf84.ts.net</div>
    <div><strong>Cidades</strong>São Paulo · Rio de Janeiro · Fortaleza</div>
    <div><strong>Autor</strong>Kayky Bezerra Da Silva · outubro de 2026</div>
  </div>
</section>
"""

HTML.write_text(f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Doa Certo · a solução completa</title>
<style>{CSS}</style></head>
<body>{CAPA}<main>{corpo}</main></body></html>""", encoding="utf-8")

subprocess.run([
    CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
    f"--print-to-pdf={PDF}", HTML.as_uri(),
], check=True, capture_output=True, timeout=120)
print(PDF, PDF.stat().st_size, "bytes")
