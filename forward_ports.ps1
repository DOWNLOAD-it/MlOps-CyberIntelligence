<#
.SYNOPSIS
Establishes an SSH tunnel to the Komodo server to bypass the university firewall.

.DESCRIPTION
This script forwards the local ports (4301, 4302, 4307, 4308, 4309) to the corresponding 
ports on the remote server (41.250.197.226) over an encrypted SSH connection.
Once running, you can access the MLSecOps Platform interfaces in your local browser 
via http://localhost:44XX from any Wi-Fi network.

.EXAMPLE
.\forward_ports.ps1 -Username "root"
#>

param (
    [Parameter(Mandatory=$false)]
    [string]$Username = "root",

    [Parameter(Mandatory=$false)]
    [string]$ServerIP = "41.250.197.226"
)

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   MLSecOps Platform - SSH Port Forwarding Tunnel      " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Connecting to $Username@$ServerIP..."
Write-Host "Forwarding the following ports to localhost:"
Write-Host "  - 4301 : Dagster Orchestrator"
Write-Host "  - 4302 : MLflow Server"
Write-Host "  - 4307 : Grafana Dashboards"
Write-Host "  - 4308 : FastAPI Backend"
Write-Host "  - 4309 : Next.js WebApp"
Write-Host ""
Write-Host "Keep this window open! The tunnel will remain active until you press Ctrl+C." -ForegroundColor Yellow
Write-Host ""

# Construct the SSH command with all port forwards
$sshCommand = "ssh -N " + 
              "-L 4301:localhost:4301 " + 
              "-L 4302:localhost:4302 " + 
              "-L 4307:localhost:4307 " + 
              "-L 4308:localhost:4308 " + 
              "-L 4309:localhost:4309 " + 
              "$Username@$ServerIP"

# Execute the command
Invoke-Expression $sshCommand

