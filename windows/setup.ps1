# Narrative.Rx - Windows Server first-time setup (Rancher Desktop backend)
# Run this once from an *Administrator* PowerShell:
#   cd C:\path\to\narrative-rx
#   powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== Narrative.Rx - Windows Server setup ===" -ForegroundColor Cyan

# ---------- 1. Rancher Desktop / docker CLI ----------
Write-Host "`n[1/6] Checking Rancher Desktop (dockerd engine)..." -ForegroundColor Yellow
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host "  ERROR: 'docker' command not found on PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Install Rancher Desktop first:"
    Write-Host "    1. Enable WSL2:  wsl --install   (reboot when prompted)"
    Write-Host "    2. Download:     https://rancherdesktop.io/"
    Write-Host "    3. Install with defaults, launch it."
    Write-Host "    4. In Rancher Desktop -> Preferences -> Container Engine, choose 'dockerd (moby)'."
    Write-Host "    5. Wait until the tray icon shows 'Kubernetes / Container engine running', then re-run this script."
    exit 1
}
try {
    $dockerVer = (docker version --format '{{.Server.Version}}' 2>$null)
    if (-not $dockerVer) { throw "no server" }
    Write-Host "  OK - dockerd $dockerVer"
} catch {
    Write-Host "  ERROR: Rancher Desktop is installed but the docker engine isn't responding." -ForegroundColor Red
    Write-Host "  Open Rancher Desktop, wait until its tray icon says 'running', then re-run."
    exit 1
}

# ---------- 2. Detect LAN IP ----------
Write-Host "`n[2/6] Detecting this machine's LAN IP..." -ForegroundColor Yellow
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.PrefixOrigin -in @('Dhcp','Manual') } |
    Where-Object { $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -notlike '127.*' -and $_.InterfaceAlias -notlike '*WSL*' -and $_.InterfaceAlias -notlike '*vEthernet*' } |
    Select-Object -First 1).IPAddress
if (-not $lanIp) { $lanIp = "127.0.0.1" }
Write-Host "  Detected: $lanIp"

# ---------- 3. Repo root ----------
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# ---------- 4. .env ----------
Write-Host "`n[3/6] Preparing .env..." -ForegroundColor Yellow
if (Test-Path .env) {
    Write-Host "  .env already exists - leaving it alone. Delete it and re-run to start over."
} else {
    if (-not (Test-Path .env.example)) {
        Write-Host "  ERROR: .env.example not found in $repoRoot" -ForegroundColor Red
        exit 1
    }
    Copy-Item .env.example .env

    # JWT secret - 64 hex chars
    $jwt = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
    (Get-Content .env) -replace '(?m)^JWT_SECRET=.*', "JWT_SECRET=$jwt" | Set-Content .env

    # Emergent LLM key
    Write-Host ""
    $llmKey = Read-Host "  Paste your EMERGENT_LLM_KEY (from https://app.emergent.sh -> Profile -> Universal Key)"
    (Get-Content .env) -replace '(?m)^EMERGENT_LLM_KEY=.*', "EMERGENT_LLM_KEY=$llmKey" | Set-Content .env

    # GHCR owner (GitHub username, lower-case)
    $ghcrOwner = Read-Host "  Your GitHub username (lower-case, e.g. 'janedoe')"
    $ghcrOwner = $ghcrOwner.ToLower()
    (Get-Content .env) -replace '(?m)^# GHCR_OWNER=.*', "GHCR_OWNER=$ghcrOwner" | Set-Content .env
    (Get-Content .env) -replace '(?m)^# IMAGE_TAG=.*', 'IMAGE_TAG=latest' | Set-Content .env

    # CORS - allow same-origin from localhost AND from the LAN IP
    (Get-Content .env) -replace '(?m)^CORS_ORIGINS=.*', "CORS_ORIGINS=http://localhost:8080,http://${lanIp}:8080" | Set-Content .env

    Write-Host "  .env created."
}

# ---------- 5. Windows Firewall ----------
Write-Host "`n[4/6] Ensuring Windows Firewall allows inbound TCP 8080..." -ForegroundColor Yellow
$ruleName = "Narrative.Rx (TCP 8080)"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  Firewall rule already exists."
} else {
    try {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound `
            -Protocol TCP -LocalPort 8080 -Action Allow -Profile Any -ErrorAction Stop | Out-Null
        Write-Host "  Firewall rule added."
    } catch {
        Write-Host "  Could not add firewall rule (requires Administrator)." -ForegroundColor Yellow
        Write-Host "  Right-click PowerShell -> Run as Administrator, then run:"
        Write-Host "    New-NetFirewallRule -DisplayName '$ruleName' -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Any"
    }
}

# ---------- 6. Pull + start ----------
Write-Host "`n[5/6] Pulling container images (first pull is 2-4 minutes)..." -ForegroundColor Yellow
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull

Write-Host "`n[6/6] Starting Narrative.Rx..." -ForegroundColor Yellow
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d

Start-Sleep -Seconds 6

Write-Host "`n=== READY ===" -ForegroundColor Green
Write-Host ""
Write-Host "  On this machine:      " -NoNewline; Write-Host "http://localhost:8080" -ForegroundColor Cyan
Write-Host "  From other office PCs: " -NoNewline; Write-Host "http://${lanIp}:8080" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Demo sign-in:  admin@dental.com  /  admin123"
Write-Host "  (Change the password on your first login.)"
Write-Host ""
Write-Host "  Auto-start on boot: open Rancher Desktop -> Preferences -> Application ->"
Write-Host "  tick 'Start at login' and 'Start in background'. The containers already"
Write-Host "  have restart: unless-stopped so they'll come back on their own."
Write-Host ""
