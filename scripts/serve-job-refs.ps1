# Brief job-refs local viewer
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$jobs = Join-Path $root "docs\refs\jobs"
$port = 8765

if (-not (Test-Path $jobs)) {
  Write-Error "Missing $jobs"
}

Write-Host "Serving $jobs"
Write-Host "Open http://127.0.0.1:$port/ui/"
Set-Location $jobs
python -m http.server $port
