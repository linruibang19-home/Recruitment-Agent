$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "data\runtime\services.json"

if (-not (Test-Path $PidFile)) {
    Write-Output "No project PID file found."
    exit 0
}

$Services = Get-Content $PidFile -Raw | ConvertFrom-Json

function Stop-ProcessTree {
    param([int]$RootProcessId)

    $Children = Get-CimInstance Win32_Process |
        Where-Object { $_.ParentProcessId -eq $RootProcessId }
    foreach ($Child in $Children) {
        Stop-ProcessTree -RootProcessId $Child.ProcessId
    }
    if (Get-Process -Id $RootProcessId -ErrorAction SilentlyContinue) {
        Stop-Process -Id $RootProcessId -ErrorAction SilentlyContinue
        Write-Output "Stopped process $RootProcessId"
    }
}

foreach ($ProcessId in @($Services.backend_pid, $Services.frontend_pid)) {
    if ($ProcessId) {
        Stop-ProcessTree -RootProcessId $ProcessId
    }
}

Remove-Item -LiteralPath $PidFile -Force
