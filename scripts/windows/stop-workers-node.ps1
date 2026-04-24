$ErrorActionPreference = "Stop"
$firewallRuleName = "DistributedCompute-WorkerPorts"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Push-Location $repoRoot
try {
    docker compose -f docker-compose.workers-only.yml down
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

Write-Host "Worker-only node stopped."