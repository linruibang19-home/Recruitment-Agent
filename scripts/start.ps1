$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $Root "data\logs"
$RuntimeDir = Join-Path $Root "data\runtime"
$PidFile = Join-Path $RuntimeDir "services.json"

New-Item -ItemType Directory -Force -Path $LogDir, $RuntimeDir | Out-Null

if (Test-Path $PidFile) {
    $Existing = Get-Content $PidFile -Raw | ConvertFrom-Json
    $Running = @($Existing.backend_pid, $Existing.frontend_pid) |
        Where-Object { $_ -and (Get-Process -Id $_ -ErrorAction SilentlyContinue) }
    if ($Running.Count -gt 0) {
        throw "Project services are already running. Run scripts\stop.ps1 first."
    }
}

$OccupiedPorts = Get-NetTCPConnection -State Listen -LocalPort 8000,5173 -ErrorAction SilentlyContinue
if ($OccupiedPorts) {
    $Summary = ($OccupiedPorts | ForEach-Object { "$($_.LocalPort):PID=$($_.OwningProcess)" }) -join ", "
    throw "Required ports are already in use: $Summary"
}

Push-Location (Join-Path $Root "backend")
try {
    python -m alembic -c alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Database migration failed."
    }
}
finally {
    Pop-Location
}

$Backend = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory (Join-Path $Root "backend") `
    -RedirectStandardOutput (Join-Path $LogDir "backend.out.log") `
    -RedirectStandardError (Join-Path $LogDir "backend.err.log") `
    -WindowStyle Hidden `
    -PassThru

$Frontend = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev", "--", "--port", "5173" `
    -WorkingDirectory (Join-Path $Root "frontend") `
    -RedirectStandardOutput (Join-Path $LogDir "frontend.out.log") `
    -RedirectStandardError (Join-Path $LogDir "frontend.err.log") `
    -WindowStyle Hidden `
    -PassThru

@{
    backend_pid = $Backend.Id
    frontend_pid = $Frontend.Id
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content -Encoding UTF8 $PidFile

Start-Sleep -Seconds 3
& (Join-Path $PSScriptRoot "status.ps1")
