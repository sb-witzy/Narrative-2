# Narrative.Rx - Windows Server install (native, no containers)

This is the "just install it on Windows Server like any other business app" guide. **No Docker, no WSL, no Hyper-V, no VMs.** Everything runs as native Windows Services.

Works on **Windows Server 2019 / 2022 / 2025** and also **Windows 10 / 11** if you'd rather use a client OS.

**Result:** the app runs as a Windows Service on one box. Any staff PC on the LAN opens `http://<office-server-ip>:8080`.

**Architecture (what actually runs):**
- **MongoDB** — native Windows Service (installed by MongoDB's MSI)
- **NarrativeRx** — Python/uvicorn process wrapped as a Windows Service by NSSM. Serves both the React UI and the `/api` endpoints on TCP 8080.
- **NSSM** — the "Non-Sucking Service Manager". Standard, free, MIT-licensed. It's how everyone runs Python on Windows.

---

## Prerequisites (install these once, in this order)

All 6 are free. Grab them on the server:

| # | Software | Where | Notes |
|---|---|---|---|
| 1 | **Git for Windows** | https://git-scm.com/download/win | Defaults are fine |
| 2 | **Python 3.12+** | https://www.python.org/downloads/windows/ | **Tick "Add python.exe to PATH"** on the first screen |
| 3 | **Node.js 20 LTS** | https://nodejs.org/ | Tick "Automatically install the necessary tools" |
| 4 | **Yarn** | After Node is installed, in a new PowerShell: `npm install -g yarn` | |
| 5 | **MongoDB Community 7** | https://www.mongodb.com/try/download/community | **During install: tick "Install MongoDB as a Service"** |
| 6 | **NSSM 2.24+** | https://nssm.cc/download | Download the zip, extract `win64\nssm.exe` into `C:\Windows\System32\` (or anywhere on PATH) |

After all 6 are installed, **open a fresh PowerShell** so all the new PATH entries take effect, then verify:

```powershell
git --version
python --version
node --version
yarn --version
nssm --version
Get-Service MongoDB
```

All six commands should return version info without errors, and `Get-Service MongoDB` should show `Running`.

---

## First-time install (~10-15 min after prereqs)

### Step 1 — Get the code

Right-click Start → **Windows PowerShell (Admin)**:

```powershell
cd C:\
git clone https://github.com/<your-username>/narrative-rx.git
cd narrative-rx
```

### Step 2 — Run the setup script

Still in **Administrator PowerShell**:

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1
```

Here's what it does (announced step by step in the output):

1. **Checks all 6 prerequisites** and prints anything missing
2. **Detects your server's LAN IP** (skips virtual adapters)
3. **Confirms the MongoDB service is running** and set to auto-start on boot
4. **Creates a Python virtualenv** at `backend\.venv\` and `pip install -r requirements.txt`
5. **Writes `backend\.env`** with a random 64-char JWT secret, correct CORS origins, and prompts for your Emergent LLM key
6. **Builds the React frontend** (`yarn install` + `yarn build` — this is the slowest step, 3-5 min)
7. **Opens Windows Firewall inbound TCP 8080**
8. **Registers `NarrativeRx` as a Windows Service** via NSSM, configured to:
   - Auto-start on boot
   - Depend on MongoDB (starts after MongoDB is up)
   - Log stdout/stderr to `windows\logs\service-*.log` (auto-rotated at 5 MB)
   - Restart automatically on crash

You'll be prompted **once** for your **Emergent LLM key** — paste it and press Enter.

When it finishes:
```
=== READY ===
  On this machine:      http://localhost:8080
  From other office PCs: http://192.168.1.50:8080

  Services now running:
    - MongoDB       (data store)
    - NarrativeRx   (backend + web UI on port 8080)
```

### Step 3 — Verify

1. On the server, open `http://localhost:8080` → login screen
2. On any other office PC on the same LAN, open `http://192.168.1.50:8080` (your real IP) → same screen
3. Sign in with `admin@dental.com` / `admin123`
4. Register your real practice account under **Sign Up**, then rotate the seeded admin

### Step 4 — Bookmark on each staff PC

- Open the LAN URL on each reception/biller PC
- Bookmark as **"Narrative.Rx"**
- Optional: Chrome/Edge → **⋮** → **Install app** → gives you a native-looking taskbar shortcut

---

## Auto-start on server boot — already done

Because both `MongoDB` and `NarrativeRx` are registered as **Windows Services with auto-start**, they come up on their own when Windows boots. No login required, no interactive session needed.

**Test it:** Restart the server. Wait ~30 seconds. Visit `http://localhost:8080` from the server console — should load. If not, check `windows\logs\service-stderr.log`.

You can view/manage both services from **services.msc** (Start → type "services") like any other Windows service.

---

## Daily operation

All in `C:\narrative-rx\windows\` — double-click:

| File | What it does |
|---|---|
| `start.bat` | Ensures MongoDB is running, then starts NarrativeRx |
| `stop.bat` | Stops NarrativeRx (leaves MongoDB running in case other apps use it) |
| `update.bat` | `git pull` + `pip install` + `yarn build` + service restart (a full deploy in one command) |
| `backup.bat` | Runs `mongodump` on the `narrative_rx` DB → `windows\backups\narrative_rx_YYYY-MM-DD_HHMM\` |

**Recommendation:** run `backup.bat` every Friday and copy the resulting folder to OneDrive / USB / a network share.

---

## Log files & health check

- **Application logs:** `C:\narrative-rx\windows\logs\service-stdout.log` and `service-stderr.log` (auto-rotated at 5 MB)
- **Live tail:**
  ```powershell
  Get-Content C:\narrative-rx\windows\logs\service-stderr.log -Tail 50 -Wait
  ```
- **Service status:**
  ```powershell
  Get-Service NarrativeRx, MongoDB
  ```
- **Restart just the app** (keeps DB running):
  ```powershell
  Restart-Service NarrativeRx
  ```

---

## Finding the server IP later

```powershell
ipconfig | findstr /R /C:"IPv4 Address"
```

**Better long-term:** set a **DHCP reservation** on the router so the server always gets the same LAN IP.

---

## Troubleshooting

**`setup.ps1` says a prereq is missing but I know I installed it**
Close and reopen PowerShell. The prereq installers add themselves to PATH, but existing PowerShell windows don't see the new PATH until they're restarted.

**Service starts then immediately stops**
Check `windows\logs\service-stderr.log` — most common causes:
- MongoDB isn't running → `Start-Service MongoDB`
- `EMERGENT_LLM_KEY` is empty or wrong in `backend\.env`
- Port 8080 already in use by IIS or another app → see below

**Port 8080 already in use** (common on Windows Server if IIS is installed)
1. Free it: `Stop-Service W3SVC; Set-Service W3SVC -StartupType Manual` (if you don't need IIS)
2. Or pick a different port. Edit `backend\.env`:
   ```
   CORS_ORIGINS=http://localhost:8090,http://192.168.1.50:8090
   ```
   Then reconfigure the service to bind to 8090:
   ```powershell
   nssm set NarrativeRx AppParameters "-m uvicorn server:app --host 0.0.0.0 --port 8090"
   Restart-Service NarrativeRx
   New-NetFirewallRule -DisplayName 'Narrative.Rx (TCP 8090)' -Direction Inbound -Protocol TCP -LocalPort 8090 -Action Allow -Profile Any
   ```
   And re-bookmark every staff PC.

**Staff PCs can't reach `http://<server-ip>:8080`**
- Confirm they're on the same subnet (compare `ipconfig` on both, first 3 octets)
- Firewall — re-run in Admin PS:
  ```powershell
  New-NetFirewallRule -DisplayName 'Narrative.Rx (TCP 8080)' -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Any
  ```
- Some corporate AV (Sophos, CrowdStrike) blocks inbound traffic to Python processes → add an exception for `C:\narrative-rx\backend\.venv\Scripts\python.exe`

**MongoDB not running after reboot**
```powershell
Set-Service MongoDB -StartupType Automatic
Start-Service MongoDB
```

**"pip install failed" during setup**
Almost always a Python architecture mismatch (32-bit Python + 64-bit Windows). Uninstall Python from **Settings → Apps**, reinstall the **64-bit** installer from python.org, tick "Add to PATH" again, delete `backend\.venv`, re-run setup.

**Restore from a backup**
```powershell
$backup = "C:\narrative-rx\windows\backups\narrative_rx_2026-02-14_1830"
& "C:\Program Files\MongoDB\Server\7.0\bin\mongorestore.exe" --uri="mongodb://localhost:27017" --gzip --drop $backup
Restart-Service NarrativeRx
```
(Adjust the `7.0` if you have a different MongoDB version.)

---

## Uninstall

```powershell
# Stop and remove the service
Stop-Service NarrativeRx -ErrorAction SilentlyContinue
nssm remove NarrativeRx confirm

# Remove firewall rule
Remove-NetFirewallRule -DisplayName 'Narrative.Rx (TCP 8080)' -ErrorAction SilentlyContinue

# Remove the code
Remove-Item -Recurse -Force C:\narrative-rx
```

MongoDB stays installed (it's useful for other things). Uninstall it from **Settings → Apps → Installed apps** if you don't want it either.

---

## Why native is actually a good fit here

- **No virtualization layer** = fewer things to break, no BIOS surprises
- **Standard Windows admin tools work** (services.msc, Event Viewer, Task Manager)
- **Standard backup practice** — snapshot the whole VM/box OR just the mongodump folder
- **Update = `git pull` + one script** — no image registry, no CI pipeline needed
- **Every dependency is signed & installed by its official publisher** — no third-party container images to trust
- **Uses only ~500 MB RAM idle** vs 2-3 GB for the container-based options

You give up:
- Portability (moving to another server = re-run setup, not just re-pull images)
- Isolation between apps (if Python breaks, it could affect other Python apps on the same box)

For a single-office deployment, the trade-off is worth it.
