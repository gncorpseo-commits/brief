# Brief API + job refs UI
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$port = 8765

Write-Host "Brief UI+API  http://127.0.0.1:$port/ui/"
Write-Host "Health        http://127.0.0.1:$port/api/health"
Write-Host "Refs JSON     http://127.0.0.1:$port/refs/index.json"

python -m uvicorn brief.api:app --app-dir src --host 127.0.0.1 --port $port --reload
