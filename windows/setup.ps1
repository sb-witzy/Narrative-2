# Narrative.Rx - Windows Server first-time setup (Podman + Hyper-V)
#
# Prereqs before running this:
#   1. Hyper-V role installed (setup.ps1 will check and prompt if missing)
#   2. Podman for Windows 5.x installed:  https://github.com/containers/podman/releases
#      (Grab podman-<version>-setup.exe and install with defaults)
#   3. Python 3.10+ installed:  https://www.python.org/downloads/windows/
#      (tick "Add Python to PATH" during install)
#
# Run this once from an *Administrator* PowerShell:
#   cd C:\path\to\narrative-rx
#   powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== Narrative.Rx - Windows Server setup (Podman) ===" -ForegroundColor Cyan

# ---------- 1. Hyper-V ----------
Write-Host "`n[1/8] Checking Hyper-V..." -ForegroundColor Yellow
$hv = Get-WindowsFeature -Name Hyper-V -ErrorAction SilentlyContinue
if (-not $hv -or $hv.InstallState -ne 'Installed') {
    Write-Host "  Hyper-V is NOT installed." -ForegroundColor Red
    Write-Host "  Install it (this requires a reboot):" -ForegroundColor Yellow
    Write-Host "    Install-WindowsFeature -Name Hyper-V -IncludeManagementTools -Restart"
    Write-Host "  After the reboot, log back in and re-run this script."
    exit 1
}
Write-Host "  OK - Hyper-V installed"

# ---------- 2. Podman ----------
Write-Host "`n[2/8] Checking Podman..." -ForegroundColor Yellow
$podmanCmd = Get-Command podman -ErrorAction SilentlyContinue
if (-not $podmanCmd) {
    Write-Host "  ERROR: 'podman' command not found on PATH." -ForegroundColor Red
    Write-Host "  Install Podman for Windows:"
    Write-Host "    https://github.com/containers/podman/releases"
    Write-Host "  Download the latest 'podman-*-setup.exe', install with defaults, open a NEW PowerShell, then re-run this script."
    exit 1
}
$podmanVer = (podman --version) -replace 'podman version ', ''
Write-Host "  OK - podman $podmanVer"

# ---------- 3. Python + podman-compose ----------
Write-Host "`n[3/8] Checking podman-compose..." -ForegroundColor Yellow
$composeCmd = Get-Command podman-compose -ErrorAction SilentlyContinue
if (-not $composeCmd) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Host "  ERROR: Python not found. Install Python 3.10+ from https://www.python.org/downloads/windows/" -ForegroundColor Red
        Write-Host "  Tick 'Add Python to PATH' during install, open a NEW PowerShell, re-run this script."
        exit 1
    }
    Write-Host "  Installing podman-compose via pip..."
    python -m pip install --upgrade pip *> $null
    python -m pip install podman-compose
    if (-not (Get-Command podman-compose -ErrorAction SilentlyContinue)) {
        Write-Host "  ERROR: podman-compose still not on PATH after pip install." -ForegroundColor Red
        Write-Host "  Check where pip put it:  python -m pip show -f podman-compose"
        exit 1
    }
}
Write-Host "  OK - podman-compose available"

# ---------- 4. Podman machine (Hyper-V VM that runs containers) ----------
Write-Host "`n[4/8] Ensuring podman machine (Hyper-V VM) is running..." -ForegroundColor Yellow
$machines = (podman machine list --format '{{.Name}}' 2>$null)
if (-not $machines) {
    Write-Host "  Initializing podman machine on Hyper-V (this takes 2-3 min the first time)..."
    podman machine init --rootful --provider hyperv --cpus 2 --memory 4096 --disk-size 20
}

# Start it if not running
$running = (podman machine list --format '{{.LastUp}}' 2>$null) -match 'Currently running'
if (-not $running) {
    Write-Host "  Starting podman machine..."
    podman machine start
}
Write-Host "  OK - podman machine running"

# ---------- 5. Detect LAN IP ----------
Write-Host "`n[5/8] Detecting this machine's LAN IP..." -ForegroundColor Yellow
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.PrefixOrigin -in @('Dhcp','Manual') } |
    Where-Object { $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -notlike '127.*' -and $_.InterfaceAlias -notlike '*vEthernet*' -and $_.InterfaceAlias -notlike '*WSL*' -and $_.InterfaceAlias -notlike '*podman*' } |
    Select-Object -First 1).IPAddress
if (-not $lanIp) { $lanIp = "127.0.0.1" }
Write-Host "  Detected: $lanIp"

# ---------- 6. Repo root + .env ----------
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "`n[6/8] Preparing .env..." -ForegroundColor Yellow
if (Test-Path .env) {
    Write-Host "  .env already exists - leaving it alone. Delete it and re-run to start over."
} else {
    if (-not (Test-Path .env.example)) {
        Write-Host "  ERROR: .env.example not found in $repoRoot" -ForegroundColor Red
        exit 1
    }
    Copy-Item .env.example .env

    $jwt = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
    (Get-Content .env) -replace '(?m)^JWT_SECRET=.*', "JWT_SECRET=$jwt" | Set-Content .env

    Write-Host ""
    $llmKey = Read-Host "  Paste your EMERGENT_LLM_KEY (from https://app.emergent.sh -> Profile -> Universal Key)"
    (Get-Content .env) -replace '(?m)^EMERGENT_LLM_KEY=.*', "EMERGENT_LLM_KEY=$llmKey" | Set-Content .env

    $ghcrOwner = Read-Host "  Your GitHub username (lower-case, e.g. 'janedoe')"
    $ghcrOwner = $ghcrOwner.ToLower()
    (Get-Content .env) -replace '(?m)^# GHCR_OWNER=.*', "GHCR_OWNER=$ghcrOwner" | Set-Content .env
    (Get-Content .env) -replace '(?m)^# IMAGE_TAG=.*', 'IMAGE_TAG=latest' | Set-Content .env

    (Get-Content .env) -replace '(?m)^CORS_ORIGINS=.*', "CORS_ORIGINS=http://localhost:8080,http://${lanIp}:8080" | Set-Content .env

    Write-Host "  .env created."
}

# ---------- 7. Windows Firewall ----------
Write-Host "`n[7/8] Ensuring Windows Firewall allows inbound TCP 8080..." -ForegroundColor Yellow
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

# ---------- 8. Pull + start ----------
Write-Host "`n[8/8] Pulling images and starting containers..." -ForegroundColor Yellow
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d

Start-Sleep -Seconds 6

Write-Host "`n=== READY ===" -ForegroundColor Green
Write-Host ""
Write-Host "  On this machine:      " -NoNewline; Write-Host "http://localhost:8080" -ForegroundColor Cyan
Write-Host "  From other office PCs: " -NoNewline; Write-Host "http://${lanIp}:8080" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Demo sign-in:  admin@dental.com  /  admin123"
Write-Host "  (Change the password on your first login.)"
Write-Host ""
Write-Host "  Auto-start on boot: see WINDOWS_INSTALL.md section 'Auto-start' -"
Write-Host "  we register a Windows Scheduled Task that runs on system startup."
Write-Host ""
