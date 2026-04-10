# scripts/dev.ps1 — run uvicorn for local development on Windows (PowerShell)
# Usage (from project root):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\dev.ps1

# Config
$AppModule = "main:app"
$HostAddr  = "127.0.0.1"
$Port      = 8000

Write-Host "Starting uvicorn (dev) $AppModule on $HostAddr`:$Port (reload, debug logs)"
uv run uvicorn $AppModule --host $HostAddr --port $Port --reload --log-level debug
