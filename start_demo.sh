#!/usr/bin/env bash
# Sobe a API (porta 8000) e o site (porta 3000) para a demo.
#
#   ./start_demo.sh           # usa o banco existente (ou cria com dados de demo)
#   ./start_demo.sh --reset   # recria os dados de demo antes de subir
#
# Funciona no Git Bash (Windows), WSL, Linux e macOS. Ctrl+C derruba os dois.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"

cd "$RAIZ/api"
if [ ! -d .venv ]; then
  echo "> Criando ambiente Python…"
  python3 -m venv .venv 2>/dev/null || python -m venv .venv
fi
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=.venv/Scripts/python; fi
echo "> Instalando dependências da API…"
"$PY" -m pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env

if [ "${1:-}" = "--reset" ] || [ ! -f doacerto.db ]; then
  echo "> Carregando dados de demonstração…"
  "$PY" -m app.seed
fi

echo "> API em http://localhost:8000 (docs em /docs)"
"$PY" -m uvicorn app.main:app --port 8000 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT INT TERM

cd "$RAIZ/web"
if [ ! -d node_modules ]; then
  echo "> Instalando dependências do site…"
  npm install --no-audit --no-fund
fi
echo "> Site em http://localhost:3000  |  Central de operações em http://localhost:3000/operacao"
npm run dev
