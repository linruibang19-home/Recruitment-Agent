$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ProfileDir = Join-Path $Root "data\profiles\boss-chrome"
$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"

if (-not (Test-Path $ChromePath)) {
    throw "Google Chrome was not found at: $ChromePath"
}

$BrowserStatus = $null
try {
    $BrowserStatus = Invoke-RestMethod "http://127.0.0.1:8000/api/automation/browser/status"
} catch {
    $BrowserStatus = $null
}

if ($BrowserStatus -and $BrowserStatus.running) {
    throw "Stop the browser session in Recruitment Agent before running this script."
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
Start-Process -FilePath $ChromePath `
    -ArgumentList "--user-data-dir=$ProfileDir", "https://sao.zhipin.com/" `
    -WindowStyle Normal

Write-Output "BOSS login window opened."
Write-Output "Complete QR login, then close that Chrome window before starting browser automation."
