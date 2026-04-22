param(
    [Parameter(Mandatory = $true)]
    [string]$OrchestratorIp,

    [ValidateRange(1, 8)]
    [int]$WorkerCount = 4,

    [int]$OrchestratorPort = 8000,

    [string]$ComputerName = $env:COMPUTERNAME
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$composeFile = Join-Path $repoRoot "docker-compose.workers-only.yml"

if (-not (Test-Path $composeFile)) {
    throw "Cannot find docker-compose.workers-only.yml at $composeFile"
}

$lanIp = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "169.254.*" -and
        $_.IPAddress -ne "127.0.0.1" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Sort-Object -Property InterfaceMetric |
    Select-Object -First 1 -ExpandProperty IPAddress
)

if (-not $lanIp) {
    throw "Unable to auto-detect LAN IPv4 address."
}

$env:ORCHESTRATOR_URL = "http://${OrchestratorIp}:${OrchestratorPort}"
$env:WORKER_HOST_IP = $lanIp
$env:COMPUTER_NAME = $ComputerName

$workerServices = 1..$WorkerCount | ForEach-Object { "worker$_" }

Write-Host "Starting worker-only node with $WorkerCount worker(s)..."
Write-Host "  ORCHESTRATOR_URL=$($env:ORCHESTRATOR_URL)"
Write-Host "  WORKER_HOST_IP=$($env:WORKER_HOST_IP)"
Write-Host "  COMPUTER_NAME=$($env:COMPUTER_NAME)"

Push-Location $repoRoot
try {
    docker compose -f docker-compose.workers-only.yml up -d --build @workerServices
}
finally {
    Pop-Location
}

Write-Host "Done. Workers should appear in orchestrator /workers within a few seconds."