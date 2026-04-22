param(
    [ValidateRange(1, 8)]
    [int]$WorkerCount = 8
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$workerServices = 1..$WorkerCount | ForEach-Object { "worker$_" }
$services = @("orchestrator", "frontend") + $workerServices

Push-Location $repoRoot
try {
    Write-Host "Starting main stack with $WorkerCount worker(s)..."
    docker compose up -d --build @services
}
finally {
    Pop-Location
}

Write-Host "Done. UI: http://localhost:3000  API: http://localhost:8000"