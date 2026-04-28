param(
    [Parameter(Mandatory = $true)]
    [string]$OrchestratorIp,

    [ValidateRange(1, 8)]
    [int]$WorkerCount = 4,

    [int]$OrchestratorPort = 8000,

    [string]$ComputerName = $env:COMPUTERNAME,

    # Override auto-detected LAN IP if detection picks up a Docker/VM adapter
    [string]$WorkerHostIp = ""
)

$ErrorActionPreference = "Stop"
$firewallRuleName = "DistributedCompute-WorkerPorts"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$composeFile = Join-Path $repoRoot "docker-compose.workers-only.yml"

if (-not (Test-Path $composeFile)) {
    throw "Cannot find docker-compose.workers-only.yml at $composeFile"
}

$lanIp = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "169.254.*" -and   # APIPA
        $_.IPAddress -ne "127.0.0.1" -and        # loopback
        $_.IPAddress -notlike "172.16.*" -and     # Docker / Hyper-V / WSL
        $_.IPAddress -notlike "172.17.*" -and
        $_.IPAddress -notlike "172.18.*" -and
        $_.IPAddress -notlike "172.19.*" -and
        $_.IPAddress -notlike "172.2*.*" -and
        $_.IPAddress -notlike "172.3*.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Sort-Object -Property InterfaceMetric |
    Select-Object -First 1 -ExpandProperty IPAddress
)

if (-not $lanIp) {
    throw "Unable to auto-detect LAN IPv4 address."
}

$env:ORCHESTRATOR_URL = "http://${OrchestratorIp}:${OrchestratorPort}"
$env:WORKER_HOST_IP = if ($WorkerHostIp) { $WorkerHostIp } else { $lanIp }
$env:COMPUTER_NAME = $ComputerName

$workerServices = 1..$WorkerCount | ForEach-Object { "worker$_" }
$workerPorts = 1..$WorkerCount | ForEach-Object { 8100 + $_ }
$portList = ($workerPorts -join ",")

try {
    $existingRule = Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
    if ($existingRule) {
        Remove-NetFirewallRule -DisplayName $firewallRuleName | Out-Null
    }

    New-NetFirewallRule `
        -DisplayName $firewallRuleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $workerPorts | Out-Null

    Write-Host "  Firewall rule '$firewallRuleName' allows TCP ports: $portList"
}
catch {
    Write-Warning "Failed to configure Windows firewall rule '$firewallRuleName'. Run this script as Administrator if orchestrator cannot reach workers."
}

Write-Host ""
Write-Host "Starting worker-only node with $WorkerCount worker(s)..."
Write-Host "  ORCHESTRATOR_URL=$($env:ORCHESTRATOR_URL)"
Write-Host "  WORKER_HOST_IP=$($env:WORKER_HOST_IP)  <<< workers will register with this LAN IP"
Write-Host "  COMPUTER_NAME=$($env:COMPUTER_NAME)"
Write-Host ""
Write-Host "If the IP above is a Docker/VM address (172.x.x.x) instead of your real LAN IP,"
Write-Host "stop here and re-run with: -WorkerHostIp <your-lan-ip>"
Write-Host ""

Push-Location $repoRoot
try {
    docker compose -f docker-compose.workers-only.yml up -d --build @workerServices
}
finally {
    Pop-Location
}

Write-Host "Done. Workers should appear in orchestrator /workers within a few seconds."