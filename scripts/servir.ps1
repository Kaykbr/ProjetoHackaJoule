<#
.SYNOPSIS
  Sobe o Doa Certo em modo produção para o link público (Tailscale Funnel).

.DESCRIPTION
  - API (uvicorn, sem --reload) em 127.0.0.1:8100, com banco próprio (api/doacerto_publico.db).
  - Site (next start) em 127.0.0.1:3100; ele repassa /api/* para a API.
  - Portas diferentes das de desenvolvimento (3000/8000): dá para continuar programando ao lado.
  - Gera um ADMIN_TOKEN na primeira vez (scripts/.admin-token): só quem abre a central com
    ?admin=<token> vê "Reiniciar demo".
  - Logs em logs/api.log e logs/web.log.

  Roda sozinho no logon do Windows pela tarefa agendada "DoaCerto" (ver scripts/instalar-tarefa.ps1).

.PARAMETER Build
  Refaz o build do site antes de subir (use depois de mudar o código do front).

.PARAMETER ResetDados
  Recria os dados de demonstração do banco público.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\servir.ps1 -Build
#>
param(
  [switch]$Build,
  [switch]$ResetDados
)

# Continue: no PowerShell 5.1, qualquer linha em stderr de um programa nativo (loguru, Next) viraria erro fatal.
$ErrorActionPreference = "Continue"
$Raiz = Split-Path -Parent $PSScriptRoot
$Api = Join-Path $Raiz "api"
$Web = Join-Path $Raiz "web"
$Logs = Join-Path $Raiz "logs"
$PortaApi = 8100
$PortaWeb = 3100
New-Item -ItemType Directory -Force $Logs | Out-Null

function Escrever($texto) {
  $linha = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $texto
  Write-Host $linha
  Add-Content -Path (Join-Path $Logs "servir.log") -Value $linha -Encoding utf8
}

function Parar-Porta($porta) {
  $conexoes = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue
  foreach ($c in $conexoes) {
    try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction Stop; Escrever "Parado o processo $($c.OwningProcess) na porta $porta" } catch {}
  }
}

function Esperar-Porta($porta, $segundos) {
  for ($i = 0; $i -lt $segundos; $i++) {
    if (Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue) { return $true }
    Start-Sleep -Seconds 1
  }
  return $false
}

# ------------------------------------------------------------------ token de admin
$ArquivoToken = Join-Path $PSScriptRoot ".admin-token"
if (-not (Test-Path $ArquivoToken)) {
  $bytes = New-Object byte[] 18
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $novo = [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_").TrimEnd("=")
  Set-Content -Path $ArquivoToken -Value $novo -NoNewline -Encoding ascii
  Escrever "ADMIN_TOKEN gerado em scripts\.admin-token"
}
$TokenAdmin = (Get-Content $ArquivoToken -Raw).Trim()

# ------------------------------------------------------------------ API
Parar-Porta $PortaApi
$Python = Join-Path $Api ".venv\Scripts\python.exe"
$env:DATABASE_URL = "sqlite:///./doacerto_publico.db"
$env:ADMIN_TOKEN = $TokenAdmin
$env:CORS_ORIGINS = "http://127.0.0.1:$PortaWeb"

if ($ResetDados -or -not (Test-Path (Join-Path $Api "doacerto_publico.db"))) {
  Escrever "Carregando dados de demonstração no banco público"
  Push-Location $Api
  & $Python -m app.seed *> (Join-Path $Logs "seed.log")
  if ($LASTEXITCODE -ne 0) { Pop-Location; Escrever "Seed falhou: veja logs\seed.log"; exit 1 }
  Pop-Location
}

Escrever "Subindo a API em 127.0.0.1:$PortaApi"
Start-Process -FilePath $Python -WorkingDirectory $Api -WindowStyle Hidden `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$PortaApi" `
  -RedirectStandardOutput (Join-Path $Logs "api.log") -RedirectStandardError (Join-Path $Logs "api-erros.log")

# ------------------------------------------------------------------ site
Parar-Porta $PortaWeb
$env:NEXT_DIST_DIR = ".next-prod"
$env:API_INTERNA_URL = "http://127.0.0.1:$PortaApi"
$env:NEXT_PUBLIC_API_URL = "/api"
$env:NODE_ENV = "production"
$Next = Join-Path $Web "node_modules\.bin\next.cmd"

if ($Build -or -not (Test-Path (Join-Path $Web ".next-prod\BUILD_ID"))) {
  Escrever "Fazendo o build de produção do site (1 a 2 minutos)"
  Push-Location $Web
  & $Next build *> (Join-Path $Logs "build.log")
  $codigo = $LASTEXITCODE
  Pop-Location
  if ($codigo -ne 0) { Escrever "Build falhou: veja logs\build.log"; exit 1 }
}

Escrever "Subindo o site em 127.0.0.1:$PortaWeb"
Start-Process -FilePath $Next -WorkingDirectory $Web -WindowStyle Hidden `
  -ArgumentList "start", "-p", "$PortaWeb", "-H", "127.0.0.1" `
  -RedirectStandardOutput (Join-Path $Logs "web.log") -RedirectStandardError (Join-Path $Logs "web-erros.log")

$apiOk = Esperar-Porta $PortaApi 40
$webOk = Esperar-Porta $PortaWeb 60
Escrever ("API: {0} | Site: {1}" -f ($(if ($apiOk) { "no ar" } else { "FALHOU (logs\api-erros.log)" })), ($(if ($webOk) { "no ar" } else { "FALHOU (logs\web-erros.log)" })))
if (-not ($apiOk -and $webOk)) { exit 1 }
