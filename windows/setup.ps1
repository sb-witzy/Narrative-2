# Narrative.Rx - Windows Server first-time setup (native, no containers)
#
# Prereqs before running this (install manually first, in this order):
#   1. Git for Windows       https://git-scm.com/download/win
#   2. Python 3.12+          https://www.python.org/downloads/windows/  (tick "Add python.exe to PATH")
#   3. Node.js 20 LTS+       https://nodejs.org/  (tick "Automatically install the necessary tools")
#   4. Yarn (after Node):    npm install -g yarn
#   5. MongoDB Community 7   https://www.mongodb.com/try/download/community
#                              -> tick "Install MongoDB as a Service" during the wizard
#                              -> tick "Install MongoDB Compass" (nice UI to peek at data)
#   6. NSSM 2.24+            https://nssm.cc/download
#                              -> Extract nssm.exe from win64\ folder into C:\Windows\System32\
#                              -> (or anywhere on PATH)
#
# Then run this once from an *Administrator* PowerShell:
#   cd C:\path\to\narrative-rx
#   powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== Narrative.Rx - Windows Server native setup ===" -ForegroundColor Cyan

# ---------- 1. Prereq checks ----------
Write-Host "`n[1/8] Checking prerequisites..." -ForegroundColor Yellow

function Require-Cmd($name, $help) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $c) {
        Write-Host "  MISSING: $name" -ForegroundColor Red
        Write-Host "    $help"
        return $false
    }
    return $true
}

$ok = $true
$ok = (Require-Cmd git    "Install Git: https://git-scm.com/download/win") -and $ok
$ok = (Require-Cmd python "Install Python 3.12+: https://www.python.org/downloads/windows/  (tick 'Add python.exe to PATH')") -and $ok
$ok = (Require-Cmd node   "Install Node.js 20 LTS: https://nodejs.org/") -and $ok
$ok = (Require-Cmd yarn   "After Node.js: npm install -g yarn") -and $ok
$ok = (Require-Cmd nssm   "Install NSSM from https://nssm.cc/download and put nssm.exe on PATH") -and $ok

# MongoDB - either the service exists (installed via MSI) OR mongod.exe on PATH
$mongoSvc = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
if (-not $mongoSvc) {
    $mongoCmd = Get-Command mongod -ErrorAction SilentlyContinue
    if (-not $mongoCmd) {
        Write-Host "  MISSING: MongoDB" -ForegroundColor Red
        Write-Host "    Install MongoDB Community from https://www.mongodb.com/try/download/community"
        Write-Host "    During install, tick 'Install MongoDB as a Service'."
        $ok = $false
    }
}
if (-not $ok) {
    Write-Host ""
    Write-Host "Install the missing tools listed above, then re-run this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "  All prerequisites present."

# ---------- 2. Repo root ----------
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
Write-Host "  Repo root: $repoRoot"

# ---------- 3. Detect LAN IP ----------
Write-Host "`n[2/8] Detecting this machine's LAN IP..." -ForegroundColor Yellow
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.PrefixOrigin -in @('Dhcp','Manual') } |
    Where-Object { $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -notlike '127.*' -and $_.InterfaceAlias -notlike '*vEthernet*' } |
    Select-Object -First 1).IPAddress
if (-not $lanIp) { $lanIp = "127.0.0.1" }
Write-Host "  Detected: $lanIp"

# ---------- 4. Ensure MongoDB service running ----------
Write-Host "`n[3/8] Ensuring MongoDB service is running..." -ForegroundColor Yellow
if ($mongoSvc) {
    if ($mongoSvc.Status -ne 'Running') {
        Start-Service "MongoDB"
        Start-Sleep -Seconds 3
    }
    Set-Service "MongoDB" -StartupType Automatic
    Write-Host "  MongoDB service is running (auto-start on boot)."
} else {
    Write-Host "  WARNING: mongod is on PATH but not installed as a Windows Service." -ForegroundColor Yellow
    Write-Host "  Re-run the MongoDB installer and tick 'Install as a Service'."
}

# ---------- 5. Backend: virtualenv + pip install ----------
Write-Host "`n[4/8] Setting up backend virtualenv..." -ForegroundColor Yellow
$venvDir = Join-Path $repoRoot "backend\.venv"
if (-not (Test-Path $venvDir)) {
    python -m venv $venvDir
}
$venvPython = Join-Path $venvDir "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip --quiet
Write-Host "  Installing Python dependencies (takes 2-3 min)..."
& $venvPython -m pip install --quiet -r "$repoRoot\backend\requirements.txt"
Write-Host "  Backend deps installed."

# ---------- 6. backend/.env ----------
Write-Host "`n[5/8] Writing backend\.env..." -ForegroundColor Yellow
$backendEnv = Join-Path $repoRoot "backend\.env"
if (Test-Path $backendEnv) {
    Write-Host "  backend\.env already exists - leaving it alone. Delete to regenerate."
} else {
    $jwt = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
    Write-Host ""
    $llmKey = Read-Host "  Paste your EMERGENT_LLM_KEY (from https://app.emergent.sh -> Profile -> Universal Key)"

    $envContent = @"
MONGO_URL=mongodb://localhost:27017
DB_NAME=narrative_rx
CORS_ORIGINS=http://localhost:8080,http://${lanIp}:8080
JWT_SECRET=$jwt
EMERGENT_LLM_KEY=$llmKey
ADMIN_EMAIL=admin@dental.com
ADMIN_PASSWORD=admin123
SERVE_FRONTEND=1
MAX_CONCURRENT_LLM=3
"@
    Set-Content -Path $backendEnv -Value $envContent -Encoding UTF8
    Write-Host "  backend\.env created."
}

# ---------- 7. Frontend build ----------
Write-Host "`n[6/8] Building the frontend (yarn install + build, takes 3-5 min)..." -ForegroundColor Yellow
# Same-origin: point REACT_APP_BACKEND_URL at nothing so API calls become /api/...
$frontendEnv = Join-Path $repoRoot "frontend\.env.production"
Set-Content -Path $frontendEnv -Value "REACT_APP_BACKEND_URL=" -Encoding UTF8

Push-Location "$repoRoot\frontend"
try {
    yarn install --frozen-lockfile 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "yarn install failed" }
    yarn build 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "yarn build failed" }
} finally {
    Pop-Location
}
Write-Host "  Frontend built to frontend\build\"

# ---------- 8. Windows Firewall ----------
Write-Host "`n[7/8] Ensuring Windows Firewall allows inbound TCP 8080..." -ForegroundColor Yellow
$ruleName = "Narrative.Rx (TCP 8080)"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  Firewall rule already exists."
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound `
        -Protocol TCP -LocalPort 8080 -Action Allow -Profile Any | Out-Null
    Write-Host "  Firewall rule added."
}

# ---------- 9. Register the backend as a Windows Service ----------
Write-Host "`n[8/8] Registering NarrativeRx Windows Service (via NSSM)..." -ForegroundColor Yellow
$svcName = "NarrativeRx"
$existingSvc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
if ($existingSvc) {
    Write-Host "  Service already exists - stopping to reconfigure..."
    Stop-Service $svcName -ErrorAction SilentlyContinue
    nssm remove $svcName confirm | Out-Null
}

$logDir = Join-Path $repoRoot "windows\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

$uvicornArgs = "-m uvicorn server:app --host 0.0.0.0 --port 8080"
nssm install $svcName $venvPython $uvicornArgs | Out-Null
nssm set $svcName AppDirectory "$repoRoot\backend" | Out-Null
nssm set $svcName AppStdout "$logDir\service-stdout.log" | Out-Null
nssm set $svcName AppStderr "$logDir\service-stderr.log" | Out-Null
nssm set $svcName AppRotateFiles 1 | Out-Null
nssm set $svcName AppRotateBytes 5242880 | Out-Null
nssm set $svcName Start SERVICE_AUTO_START | Out-Null
nssm set $svcName DisplayName "Narrative.Rx Backend + Web UI" | Out-Null
nssm set $svcName Description "Dental insurance narrative assistant. Serves web UI + API on TCP 8080." | Out-Null
nssm set $svcName DependOnService MongoDB | Out-Null

Start-Service $svcName
Start-Sleep -Seconds 5

$svc = Get-Service -Name $svcName
if ($svc.Status -ne 'Running') {
    Write-Host "  Service failed to start. Check logs at $logDir\service-stderr.log" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== READY ===" -ForegroundColor Green
Write-Host ""
Write-Host "  On this machine:      " -NoNewline; Write-Host "http://localhost:8080" -ForegroundColor Cyan
Write-Host "  From other office PCs: " -NoNewline; Write-Host "http://${lanIp}:8080" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Demo sign-in:  admin@dental.com  /  admin123"
Write-Host "  (Change the password on your first login.)"
Write-Host ""
Write-Host "  Services now running:"
Write-Host "    - MongoDB       (data store)"
Write-Host "    - NarrativeRx   (backend + web UI on port 8080)"
Write-Host ""
Write-Host "  Both are set to auto-start on boot. Manage them from services.msc"
Write-Host "  or with the batch files in windows\ (start.bat / stop.bat / update.bat / backup.bat)."
Write-Host ""
