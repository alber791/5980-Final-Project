param(
    [ValidateRange(1, 8)]
    [int]$WorkerCount = 8,

    [int]$OrchestratorPort = 8000
)

$ErrorActionPreference = "Stop"
$firewallRuleName = "DistributedCompute-OrchestratorPort"
$dockerBackendRuleName = "Docker Desktop Backend"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$workerServices = 1..$WorkerCount | ForEach-Object { "worker$_" }
$services = @("orchestrator", "frontend") + $workerServices

try {
    $dockerBackendRule = Get-NetFirewallRule -DisplayName $dockerBackendRuleName -ErrorAction SilentlyContinue
    if ($dockerBackendRule) {
        Disable-NetFirewallRule -DisplayName $dockerBackendRuleName | Out-Null
        Write-Host "Disabled blocking firewall rule '$dockerBackendRuleName'."
    }

    $existingRule = Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
    if ($existingRule) {
        Remove-NetFirewallRule -DisplayName $firewallRuleName | Out-Null
    }

    New-NetFirewallRule `
        -DisplayName $firewallRuleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $OrchestratorPort `
        -Profile Any | Out-Null

    Write-Host "Firewall rule '$firewallRuleName' allows TCP port: $OrchestratorPort"
}
catch {
    Write-Warning "Failed to configure Windows firewall rules. Run this script as Administrator if remote workers cannot reach orchestrator."
}

Push-Location $repoRoot
try {
    Write-Host "Starting main stack with $WorkerCount worker(s)..."
    docker compose up -d --build @services
}
finally {
    Pop-Location
}

Write-Host "Done. UI: http://localhost:3000  API: http://localhost:8000"