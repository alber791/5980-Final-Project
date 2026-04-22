$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Push-Location $repoRoot
try {
    docker compose -f docker-compose.workers-only.yml down
}
finally {
    Pop-Location
}

Write-Host "Worker-only node stopped."