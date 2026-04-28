$ErrorActionPreference = "Stop"
$firewallRuleName = "DistributedCompute-OrchestratorPort"
$dockerBackendRuleName = "Docker Desktop Backend"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Push-Location $repoRoot
try {
    docker compose down
}
finally {
    Pop-Location
}

try {
    $existingRule = Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
    if ($existingRule) {
        Remove-NetFirewallRule -DisplayName $firewallRuleName | Out-Null
        Write-Host "Removed firewall rule '$firewallRuleName'."
    }
    else {
        Write-Host "Firewall rule '$firewallRuleName' was not present."
    }
}
catch {
    Write-Warning "Failed to remove firewall rule '$firewallRuleName'. You may need to run this script as Administrator."
}

try {
    $dockerBackendRule = Get-NetFirewallRule -DisplayName $dockerBackendRuleName -ErrorAction SilentlyContinue
    if ($dockerBackendRule) {
        Enable-NetFirewallRule -DisplayName $dockerBackendRuleName | Out-Null
        Write-Host "Re-enabled firewall rule '$dockerBackendRuleName'."
    }
}
catch {
    Write-Warning "Failed to re-enable firewall rule '$dockerBackendRuleName'. You may need to run this script as Administrator."
}

Write-Host "Main stack stopped."
