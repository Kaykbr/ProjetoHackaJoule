<#
.SYNOPSIS
  Cria (ou recria) a tarefa agendada "DoaCerto": roda scripts\servir.ps1 a cada logon do Windows.

.DESCRIPTION
  Junto com o Tailscale (que já sobe como serviço e guarda o `funnel --bg`), faz o link público
  voltar sozinho depois de reiniciar o PC. Para remover:
    Unregister-ScheduledTask -TaskName DoaCerto -Confirm:$false
#>
$ErrorActionPreference = "Stop"
$Servir = Join-Path $PSScriptRoot "servir.ps1"

$acao = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Servir`""
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$gatilho.Delay = "PT30S"  # espera a rede subir
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "DoaCerto" -Action $acao -Trigger $gatilho -Settings $config `
  -Description "Sobe o Doa Certo (API + site) para o link público do Tailscale Funnel." -Force | Out-Null
Write-Host "Tarefa 'DoaCerto' criada: roda no logon de $env:USERNAME."
