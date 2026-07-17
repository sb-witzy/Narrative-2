# Narrative.Rx - Windows Server install (Rancher Desktop)

This is the "put it on the office server and have every staff PC hit it over the LAN" guide, written for **Windows Server 2019 / 2022 / 2025**.

Docker Desktop is **not allowed on Windows Server** (both licensing and platform). We use **Rancher Desktop** instead - free, no license fee, provides the same `docker` and `docker compose` CLIs, so every script in this repo Just Works.

**Result:** one Windows Server machine runs the app. Any staff PC on the same LAN opens `http://<office-server-ip>:8080`.

---

## What you need

- **Windows Server 2019 (build 17763+), 2022, or 2025** - kept powered on during clinic hours
- **4 GB free RAM, 10 GB free disk**
- The server reachable from other office PCs on the same LAN
- **Local Administrator** rights on the server (for WSL2 install and firewall rule)
- Your **EMERGENT_LLM_KEY** - grab from https://app.emergent.sh -> Profile -> **Universal Key**
- Your **GitHub username** (the account whose GHCR packages host the Docker images)

---

## First-time install (~20 minutes, done once)

### Step 1 - Enable WSL2 (Windows Subsystem for Linux)

Rancher Desktop needs WSL2 to host the Linux VM that runs `dockerd`. On Windows Server WSL2 is opt-in.

1. Right-click Start -> **Windows PowerShell (Admin)**
2. Run:
   ```powershell
   wsl --install --no-distribution
   ```
   > On Server 2019: this may not exist. Instead run:
   > ```powershell
   > Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -All -NoRestart
   > Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All -NoRestart
   > ```
   > Then reboot, then run `wsl --set-default-version 2`, then `wsl --update`.
3. **Reboot** when prompted.
4. After reboot, verify:
   ```powershell
   wsl --status
   ```
   It should print `Default Version: 2`.

### Step 2 - Install Rancher Desktop

1. Download the Windows installer: https://github.com/rancher-sandbox/rancher-desktop/releases (grab the latest `.msi`)
   > Or via winget: `winget install SUSE.RancherDesktop`
2. Install with defaults (yes to WSL integration when asked)
3. Launch **Rancher Desktop** from the Start menu. It'll take ~2 min the first time to provision its WSL VM.
4. When the setup wizard appears:
   - **Kubernetes:** untick "Enable Kubernetes" (we don't need it - saves ~1 GB RAM)
   - **Container Engine:** choose **`dockerd (moby)`** ← important, this is what gives you the `docker` CLI
   - Click **Accept**
5. Wait until the tray icon (bottom-right, looks like a cow silhouette) shows **"Container engine running"** (right-click it to see status).
6. Open Rancher Desktop -> **Preferences (⚙)** -> **Application**:
   - Tick ✅ **"Start at login"**
   - Tick ✅ **"Start in background"**
   - Click **Apply**

### Step 3 - Get the code

1. Install Git if not present: https://git-scm.com/download/win (defaults are fine)
2. PowerShell (Admin) again:
   ```powershell
   cd C:\
   git clone https://github.com/<your-username>/narrative-rx.git
   cd narrative-rx
   ```

### Step 4 - Run the setup script

Still in **PowerShell (Admin)**:

```powershell
cd C:\narrative-rx
powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1
```

The script:
- Verifies the docker CLI is available and `dockerd` is responding
- Detects the server's LAN IP (skips WSL / vEthernet virtual adapters)
- Generates a 64-char JWT secret
- **Prompts for your Emergent LLM key**
- **Prompts for your GitHub username** (lowercase)
- Writes `.env` with correct CORS origins
- Opens Windows Firewall inbound TCP 8080
- Pulls the two images from GHCR (~2-4 min the first time)
- Starts the stack in the background

When done, you'll see:
```
=== READY ===
  On this machine:      http://localhost:8080
  From other office PCs: http://192.168.1.50:8080
```

**Write those two URLs down.**

### Step 5 - Verify

1. On the server, open `http://localhost:8080` in Edge/Chrome -> login screen appears
2. On any other office PC on the same LAN, open `http://192.168.1.50:8080` (use your real IP) -> same screen
3. Sign in with the seeded admin:
   - Email: `admin@dental.com`
   - Password: `admin123`
4. Register a real practice account under **Sign Up**, log in as that, then delete or rotate the admin.

### Step 6 - Bookmark on each staff PC

- Open the LAN URL
- Bookmark as **"Narrative.Rx"**
- Optional: Chrome/Edge -> **⋮** menu -> **Install app** -> gives you a taskbar icon that looks native (no browser chrome, cleaner for reception staff)

---

## Daily operation

Everything's in `C:\narrative-rx\windows\` - double-click any of these:

| File | Does |
|---|---|
| `start.bat` | Bring the stack up (only needed if Rancher Desktop's autostart is off) |
| `stop.bat` | Clean shutdown - data preserved in the Docker volume |
| `update.bat` | Pull the latest images from GHCR and restart |
| `backup.bat` | Snapshot MongoDB to `windows\backups\narrative_rx_YYYY-MM-DD_HHMM.gz` |

**Recommendation:** run `backup.bat` every Friday and copy the resulting `.gz` off the server (OneDrive, network share, USB).

---

## Auto-start on boot

Because Rancher Desktop needs an interactive Windows session to run its WSL VM, the auto-start chain is:

1. **Server boots** -> Windows logs into the service account
2. **Rancher Desktop** launches (because you ticked "Start at login" + "Start in background" in Step 2)
3. **dockerd** comes up inside the WSL VM
4. **Compose containers** restart automatically thanks to `restart: unless-stopped` in `docker-compose.yml`

Test it: **Restart the server**. Wait 2 minutes. Visit `http://localhost:8080` from the server console. Should load. If not, log in interactively once - Rancher Desktop won't start under a locked / signed-out session.

If the server is **domain-joined and normally sits at the login screen**, either:
- Enable Windows **auto-login** for the service account (`netplwiz` -> untick "Users must enter a user name..."), OR
- Use a **console session keeper** (`autologon.exe` from Sysinternals) so Rancher Desktop always has a session to run in.

---

## Finding the server IP later

```powershell
ipconfig | findstr /R /C:"IPv4 Address"
```

Ignore any lines from **WSL** or **vEthernet** adapters - use the physical Ethernet / WiFi one.

**Better long-term:** set a **DHCP reservation** on the router so the server always gets the same LAN IP.

---

## Troubleshooting

**`docker: not recognized`**
Rancher Desktop hasn't finished starting, or the "Container Engine" is set to `containerd` instead of `dockerd (moby)`. Open Rancher Desktop -> Preferences -> **Container Engine** -> pick **`dockerd (moby)`** -> Apply -> wait 30 sec.

**Rancher Desktop refuses to start / "WSL2 is not installed"**
Reopen an admin PowerShell:
```powershell
wsl --update
wsl --set-default-version 2
```
Then relaunch Rancher Desktop.

**`denied: permission_denied: read_package` when pulling images**
Your GHCR packages are private. Either:
- Make them public: GitHub -> your profile -> **Packages** -> pick each package -> **Package settings** -> **Change visibility** -> Public
- Or authenticate once on the server:
  ```powershell
  $env:GHCR_PAT = "ghp_YOUR_CLASSIC_TOKEN_WITH_read:packages_SCOPE"
  $env:GHCR_PAT | docker login ghcr.io -u <your-username> --password-stdin
  ```

**Staff PCs can't reach `http://<server-ip>:8080`**
- Confirm they're on the same subnet (`ipconfig` on both, first 3 octets match)
- Windows Firewall blocked port 8080. Re-run `setup.ps1` as **Administrator**, or one-liner:
  ```powershell
  New-NetFirewallRule -DisplayName 'Narrative.Rx (TCP 8080)' -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Any
  ```
- Some corporate AV suites (Sophos, CrowdStrike) block inbound container traffic. Add an exclusion for the Rancher Desktop process.

**Port 8080 already in use (IIS, SolidWorks License Manager, etc.)**
Edit `.env` and change:
```
WEB_PORT=8090
CORS_ORIGINS=http://localhost:8090,http://192.168.1.50:8090
```
Then `windows\stop.bat` then `windows\start.bat`. Also update your firewall rule to 8090 and re-bookmark on staff PCs.

**Everything stopped - how to fully reset without losing data**
```powershell
cd C:\narrative-rx
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml down
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

**Restore from a backup**
```powershell
docker exec -i narrative-rx-mongo mongorestore --archive --gzip --db narrative_rx `
    < windows\backups\narrative_rx_2026-02-14_1830.gz
```

---

## Uninstall

```powershell
cd C:\narrative-rx
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml down -v   # -v also drops the mongo volume - data is gone
cd C:\
Remove-Item -Recurse -Force C:\narrative-rx
```

Uninstall Rancher Desktop from **Settings -> Apps -> Installed apps** if you no longer need it.
