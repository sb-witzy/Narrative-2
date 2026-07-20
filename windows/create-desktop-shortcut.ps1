# Narrative.Rx — Desktop shortcut installer
#
# Creates a proper Windows shortcut on the current user's Desktop that opens
# Narrative.Rx in Edge or Chrome (as an "app window" — no browser chrome),
# using the branded Narrative.Rx icon.
#
# Usage on a STAFF PC:
#   1. Copy this file (create-desktop-shortcut.ps1) and the accompanying
#      narrative-rx.ico onto the staff PC (any folder — Downloads is fine).
#   2. Right-click the .ps1 file -> "Run with PowerShell"
#      (Or: powershell -ExecutionPolicy Bypass -File .\create-desktop-shortcut.ps1)
#   3. Enter the URL when prompted, e.g. http://192.168.1.50:8080
#      (Or edit $Url below to hard-code it before distributing.)
#
# The shortcut launches Edge (or Chrome as a fallback) in "app mode" -
# so it looks like a native Windows app, no address bar, no tabs.

param(
    [string]$Url,
    [string]$ShortcutName = "Narrative.Rx"
)

$ErrorActionPreference = "Stop"

# ---------- 1. Resolve the URL ----------
if (-not $Url) {
    $Url = Read-Host "Enter the Narrative.Rx URL (e.g. http://192.168.1.50:8080)"
}
if ($Url -notmatch '^https?://') {
    Write-Host "URL must start with http:// or https://" -ForegroundColor Red
    exit 1
}

# ---------- 2. Locate the .ico file ----------
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$icoCandidates = @(
    (Join-Path $scriptDir 'narrative-rx.ico'),
    (Join-Path $scriptDir 'branding\narrative-rx.ico')
)
$ico = $icoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ico) {
    Write-Host "narrative-rx.ico not found next to this script." -ForegroundColor Yellow
    Write-Host "  Place narrative-rx.ico in the same folder as this .ps1 and re-run."
    Write-Host "  (Server admins: it's at C:\<repo>\windows\branding\narrative-rx.ico)"
    exit 1
}

# Copy the icon into a stable location so the shortcut survives moving the .ps1
$iconStore = Join-Path $env:APPDATA "NarrativeRx"
if (-not (Test-Path $iconStore)) { New-Item -ItemType Directory -Path $iconStore | Out-Null }
$icoInstalled = Join-Path $iconStore "narrative-rx.ico"
Copy-Item $ico $icoInstalled -Force

# ---------- 3. Locate a browser (prefer Edge, fall back to Chrome) ----------
$browser = $null
$edge   = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$chrome1 = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
$chrome2 = 'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
foreach ($p in @($edge, $chrome1, $chrome2)) {
    if (Test-Path $p) { $browser = $p; break }
}
if (-not $browser) {
    Write-Host "Neither Edge nor Chrome was found in the standard install paths." -ForegroundColor Red
    Write-Host "  Install Microsoft Edge or Google Chrome and re-run."
    exit 1
}

# ---------- 4. Create the .lnk on the Desktop ----------
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "$ShortcutName.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $browser
$shortcut.Arguments = "--app=$Url --window-size=1280,900"
$shortcut.WorkingDirectory = Split-Path -Parent $browser
$shortcut.IconLocation = "$icoInstalled,0"
$shortcut.Description = "Narrative.Rx - Dental insurance narrative writer"
$shortcut.Save()

# ---------- 5. Also pin to Start Menu (all-users) if possible ----------
try {
    $startMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    Copy-Item $lnkPath (Join-Path $startMenu "$ShortcutName.lnk") -Force
    $pinnedToStart = $true
} catch {
    $pinnedToStart = $false
}

Write-Host ""
Write-Host "  Desktop shortcut created:  $lnkPath" -ForegroundColor Green
Write-Host "  Opens $browser in app-window mode pointing at $Url"
if ($pinnedToStart) { Write-Host "  Also added to the Start Menu." -ForegroundColor Green }
Write-Host ""
Write-Host "  Double-click the desktop icon to launch Narrative.Rx."
Write-Host ""
