$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "data\runtime\services.json"

if (Test-Path $PidFile) {
    $Services = Get-Content $PidFile -Raw | ConvertFrom-Json
    Write-Output "Started at: $($Services.started_at)"
    foreach ($Entry in @(
        @{ Name = "Backend"; Id = $Services.backend_pid; Url = "http://127.0.0.1:8000/docs" },
        @{ Name = "Frontend"; Id = $Services.frontend_pid; Url = "http://127.0.0.1:5173" }
    )) {
        $Running = [bool](Get-Process -Id $Entry.Id -ErrorAction SilentlyContinue)
        $State = if ($Running) { "running" } else { "stopped" }
        Write-Output "$($Entry.Name): $State PID=$($Entry.Id) $($Entry.Url)"
    }
} else {
    Write-Output "No PID file found. Checking listening ports."
}

Get-NetTCPConnection -State Listen -LocalPort 8000,5173 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, OwningProcess
