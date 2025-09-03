# scripts/dev/dev.ps1 — run uvicorn for local development on Windows (PowerShell)
# Usage (from project root):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\dev\dev.ps1

# Config — change if needed
$VenvActivate = ".\venv\Scripts\Activate.ps1"   # path to Activate.ps1
$AppModule    = "main:app"
$HostAddr     = "127.0.0.1"
$Port         = 8000

# Activate venv if exists
if (Test-Path $VenvActivate) {
    Write-Host "Activating venv: $VenvActivate"
    & $VenvActivate
} else {
    Write-Warning "Virtualenv activate script not found at $VenvActivate. Using system python."
}

Write-Host "Starting uvicorn (dev) $AppModule on $HostAddr`:$Port (reload, debug logs)"
uvicorn $AppModule --host $HostAddr --port $Port --reload --log-level debug
