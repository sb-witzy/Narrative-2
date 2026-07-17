# Narrative.Rx - Windows Server install (Podman + Hyper-V, no WSL)

This is the "put it on the office server and have every staff PC hit it over the LAN" guide, written for **Windows Server 2019 / 2022 / 2025** where **WSL2 is not available**.

We use **Podman** (free, open-source) with the **Hyper-V** provider. Podman runs a tiny Linux VM in Hyper-V that hosts the containers. From the user's perspective, `podman` behaves like `docker`.

**Result:** one Windows Server machine runs the app. Any staff PC on the same LAN opens `http://<office-server-ip>:8080`.

---

## What you need

- **Windows Server 2019 (build 17763+), 2022, or 2025** kept powered on during clinic hours
- **CPU with virtualization support enabled in BIOS** (VT-x on Intel, AMD-V on AMD) - required for Hyper-V
- **6 GB free RAM, 25 GB free disk** (Hyper-V VM gets 4 GB, containers get the rest)
- **Local Administrator** on the server (needed to install Hyper-V + open the firewall)
- Your **EMERGENT_LLM_KEY** - grab from https://app.emergent.sh -> Profile -> **Universal Key**
- Your **GitHub username** (the account whose GHCR packages host the images)

---

## First-time install (~30 minutes total, done once)

### Step 1 - Install the Hyper-V role (~5 min + one reboot)

Right-click Start -> **Windows PowerShell (Admin)**:

```powershell
Install-WindowsFeature -Name Hyper-V -IncludeManagementTools -Restart
```

The server **will reboot automatically**. Log back in when it comes back up.

Verify Hyper-V is up:
```powershell
Get-WindowsFeature Hyper-V | Format-Table Name, InstallState
```
Should say `Installed`.

> **If this errors with "Hyper-V cannot be installed":** virtualization is disabled in BIOS. Reboot into BIOS/UEFI (usually F2/Del at boot), enable **Intel VT-x** or **AMD-V** (sometimes called "SVM"), save, then re-run the install command. If you're already inside a VM, enable **nested virtualization** on the host.

### Step 2 - Install Podman for Windows (~3 min)

1. Download the latest **Podman for Windows** installer: https://github.com/containers/podman/releases (grab the file named `podman-<version>-setup.exe`)
2. Run it, accept defaults
3. Close and reopen PowerShell (Admin) so `podman` shows up on PATH
4. Verify:
   ```powershell
   podman --version
   ```
   Should print something like `podman version 5.4.x`.

### Step 3 - Install Python (for podman-compose) (~3 min)

1. Download: https://www.python.org/downloads/windows/ (any 3.10+)
2. Run the installer -- **tick "Add python.exe to PATH"** on the first screen -- and click Install
3. Close and reopen PowerShell (Admin)
4. Verify:
   ```powershell
   python --version
   ```

### Step 4 - Get the code

```powershell
cd C:\
git clone https://github.com/<your-username>/narrative-rx.git
cd narrative-rx
```

> If Git isn't installed: https://git-scm.com/download/win (defaults are fine)

### Step 5 - Run the setup script (~5 min)

Still in **PowerShell (Admin)** and in the repo folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1
```

The script:
- Verifies Hyper-V is installed
- Verifies `podman` is on PATH
- `pip install podman-compose` if not already installed
- Runs `podman machine init --rootful --provider hyperv --cpus 2 --memory 4096 --disk-size 20`  (creates the Linux VM inside Hyper-V, takes ~2 min the first time)
- Runs `podman machine start`
- Detects the server's LAN IP (skips virtual/vEthernet adapters)
- Prompts for your **Emergent LLM key** and **GitHub username**
- Writes `.env` with correct CORS origins
- Opens Windows Firewall inbound TCP 8080
- Pulls the images from GHCR and starts the stack

When done you'll see:
```
=== READY ===
  On this machine:      http://localhost:8080
  From other office PCs: http://192.168.1.50:8080
```

**Save both URLs.**

### Step 6 - Verify

1. On the server, open `http://localhost:8080` -> login screen
2. On any other office PC on the same LAN, open `http://192.168.1.50:8080` (your real IP) -> same screen
3. Sign in as `admin@dental.com` / `admin123`
4. Register your real practice account under **Sign Up**, then rotate/delete the seeded admin

### Step 7 - Bookmark on staff PCs

- Open the LAN URL on each reception/biller PC
- Bookmark as **"Narrative.Rx"**
- Optional: Chrome/Edge -> **⋮** -> **Install app** -> gives you a native-looking taskbar shortcut

---

## Daily operation

All scripts live in `C:\narrative-rx\windows\` - double-click any of them:

| File | What it does |
|---|---|
| `start.bat` | Starts the podman machine (if stopped) and brings the stack up |
| `stop.bat` | Cleanly stops the containers (data is preserved in the volume) |
| `update.bat` | Pulls the latest images from GHCR and restarts the stack |
| `backup.bat` | Snapshots MongoDB to `windows\backups\narrative_rx_YYYY-MM-DD_HHMM.gz` |

**Recommendation:** run `backup.bat` every Friday and copy the resulting `.gz` off the server (OneDrive, USB, network share).

---

## Auto-start on system boot

**Podman on Windows does not auto-start by default** - unlike Docker Desktop, there's no tray app. We register a Windows Scheduled Task that runs `start.bat` at system startup.

Run this in an **Administrator PowerShell** (once):

```powershell
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c C:\narrative-rx\windows\start.bat" -WorkingDirectory "C:\narrative-rx"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName "NarrativeRx-AutoStart" -Action $action -Trigger $trigger -Principal $principal -Settings $settings
```

**Test it:** reboot the server. After ~90 seconds visit `http://localhost:8080` from the console - it should load. The delay is Hyper-V spinning up the podman VM.

To remove later: `Unregister-ScheduledTask -TaskName "NarrativeRx-AutoStart" -Confirm:$false`

---

## Finding the server IP later

```powershell
ipconfig | findstr /R /C:"IPv4 Address"
```

Ignore any lines for **vEthernet**, **podman**, or virtual adapters - use the physical Ethernet/WiFi one.

**Better long-term:** set a **DHCP reservation** on the router so the server always gets the same LAN IP.

---

## Troubleshooting

**`Install-WindowsFeature: Hyper-V cannot be installed`**
Virtualization is disabled in BIOS/UEFI. Reboot -> BIOS -> enable **Intel VT-x** or **AMD-V** (may be called "SVM Mode") -> save -> retry. If already in a VM, enable nested virtualization on the parent host.

**`podman machine start` fails with `Error: hyperv: exit status 1`**
Almost always means Hyper-V's Virtual Machine Management Service isn't running:
```powershell
Start-Service vmms
Set-Service vmms -StartupType Automatic
```
Then retry.

**`podman: command not found` after installing Podman**
You need to close and reopen PowerShell for the PATH update to take effect. Or manually run `refreshenv` if you have Chocolatey installed.

**`podman-compose: command not found` after `pip install`**
Python's Scripts folder isn't on PATH. Either reinstall Python with the "Add Python to PATH" box ticked, or manually add `C:\Users\<you>\AppData\Local\Programs\Python\Python3XX\Scripts` to PATH.

**`denied: permission_denied: read_package` when pulling from GHCR**
Your GHCR packages are private. Either:
- Make them public: GitHub -> Profile -> **Packages** -> each package -> **Package settings** -> **Change visibility** -> Public
- Or authenticate once:
  ```powershell
  $env:GHCR_PAT = "ghp_YOUR_CLASSIC_TOKEN_WITH_read:packages_SCOPE"
  $env:GHCR_PAT | podman login ghcr.io -u <your-username> --password-stdin
  ```

**Staff PCs can't reach `http://<server-ip>:8080`**
- Same subnet? Compare `ipconfig` on server and client - first 3 octets should match
- Firewall rule missing - re-run `setup.ps1` **as Administrator**, or one-liner:
  ```powershell
  New-NetFirewallRule -DisplayName 'Narrative.Rx (TCP 8080)' -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Any
  ```
- Some AV suites (Sophos, CrowdStrike) block inbound container traffic - add an exception for `gvproxy.exe` (Podman's port forwarder, in `C:\Program Files\RedHat\Podman\`)

**Port 8080 already in use (IIS License Manager, etc.)**
Edit `.env`:
```
WEB_PORT=8090
CORS_ORIGINS=http://localhost:8090,http://192.168.1.50:8090
```
Run `windows\stop.bat` then `windows\start.bat`. Update the firewall rule to 8090 and re-bookmark on staff PCs.

**Everything is broken - how to fully reset the container stack (keeps data)**
```powershell
cd C:\narrative-rx
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml down
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

**Restore from a backup**
```powershell
podman exec -i narrative-rx-mongo mongorestore --archive --gzip --db narrative_rx `
    < windows\backups\narrative_rx_2026-02-14_1830.gz
```

**"Where is my Mongo data actually stored?"**
Inside the podman Hyper-V VM, in a named volume `mongo-data`. It's not a folder on the Windows host. That's why backups use `podman exec ... mongodump` streamed to a Windows file - it's the portable way to get data out.

---

## Uninstall

```powershell
cd C:\narrative-rx
podman-compose -f docker-compose.yml -f docker-compose.ghcr.yml down -v   # -v also drops the mongo volume - data is gone
podman machine stop
podman machine rm --force
cd C:\
Remove-Item -Recurse -Force C:\narrative-rx
Unregister-ScheduledTask -TaskName "NarrativeRx-AutoStart" -Confirm:$false 2>$null
```

Uninstall Podman from **Settings -> Apps -> Installed apps** if you don't need it anymore. Remove the Hyper-V role with `Uninstall-WindowsFeature -Name Hyper-V -Restart` (requires reboot).
