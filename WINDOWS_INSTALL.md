# Narrative.Rx — Windows office server install

This is the "put it on the front-desk PC or a spare Windows box so everyone in the office can use it" guide.

**Result:** the app runs on one Windows machine. Any staff computer on the same WiFi opens it at `http://<office-server-ip>:8080` and signs in.

---

## What you need

- A Windows 10 / 11 / Server 2019+ machine that will stay powered on during clinic hours
- 4 GB free RAM, 5 GB free disk
- The machine reachable from other office PCs on the same network (WiFi or ethernet)
- Your **EMERGENT_LLM_KEY** — grab from https://app.emergent.sh → Profile → Universal Key
- Your **GitHub username** (the one whose repo hosts the Docker images)

## First-time install (~10 minutes, done once)

### Step 1 — Docker Desktop

1. Download **Docker Desktop for Windows**: https://www.docker.com/products/docker-desktop
2. Install (default options are fine — WSL2 backend is fine too)
3. Launch Docker Desktop. Wait ~30 seconds until the whale icon in the tray stops animating.
4. Docker Desktop → **Settings ⚙** → **General** → tick **"Start Docker Desktop when you log in"**. Click **Apply & restart**.

### Step 2 — Get the code

1. Install Git if you don't have it: https://git-scm.com/download/win
2. Open **PowerShell** and pick a folder (e.g. `C:\`):
   ```powershell
   cd C:\
   git clone https://github.com/<your-username>/narrative-rx.git
   cd narrative-rx
   ```

### Step 3 — Run the setup script

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\setup.ps1
```

The script:
- checks Docker
- finds the machine's LAN IP
- generates a JWT secret
- **prompts you for your Emergent LLM key** — paste it and press Enter
- **prompts you for your GitHub username** (lower-case)
- writes `.env`
- opens Windows Firewall port 8080 for inbound traffic (requires Administrator — right-click PowerShell → **Run as Administrator** if it asks)
- pulls the Docker images from GHCR
- starts Narrative.Rx

**When it finishes it prints two URLs — save them.** Example:
```
=== READY ===
  On this machine:      http://localhost:8080
  From other office PCs: http://192.168.1.50:8080
```

### Step 4 — Verify it works

1. On the server itself, open `http://localhost:8080` in a browser
2. On a different office computer connected to the same WiFi, open `http://<server-ip>:8080`
3. Sign in with `admin@dental.com` / `admin123`
4. **Change the admin password immediately** (top-right → account — TODO in the app)

### Step 5 — Bookmark it on every staff computer

On every reception/biller computer:
- Open the office server URL
- Bookmark it as **"Narrative.Rx"**
- Optional: Chrome/Edge → three-dot menu → **Install app** — turns it into a taskbar shortcut that looks like a native Windows app

---

## Daily operation

Everything lives under `C:\narrative-rx\windows\` — double-click the batch files:

| File | What it does |
|---|---|
| `start.bat` | Start the app. Only needed if Docker Desktop wasn't set to auto-start. |
| `stop.bat` | Stop the app cleanly (data is preserved). |
| `update.bat` | Pull the newest images from GHCR and restart. Do this whenever you push a new build. |
| `backup.bat` | Snapshot the MongoDB into `windows\backups\narrative_rx_YYYY-MM-DD_HHMM.gz` |

## Auto-start on boot — confirm it's working

1. Docker Desktop → **Settings** → **General** → make sure **"Start Docker Desktop when you log in"** is ticked
2. `docker-compose.yml` already sets `restart: unless-stopped` on every service — so as soon as Docker Desktop starts, the containers start automatically
3. **Test:** log out and log back in. Wait ~1 minute. Visit `http://localhost:8080` — should load

If the server machine isn't set to auto-login on Windows boot, either:
- Enable Windows auto-login (Settings → Accounts → Sign-in options), OR
- Use Windows **Task Scheduler** with a "At startup" trigger running `C:\narrative-rx\windows\start.bat`. That will fail until you first log in and Docker starts, but combined with auto-login it works around the "requires interactive session" issue.

---

## Finding the server's IP later

If DHCP changed it and you forgot:

```powershell
ipconfig | findstr /R /C:"IPv4 Address"
```

Better long-term: **set a DHCP reservation** on your office router so the server always gets the same IP (usually a checkbox next to the device in the router's LAN settings).

---

## Troubleshooting

**Setup fails with "docker: not recognized"**
Docker Desktop isn't installed or hasn't finished starting. Wait for the whale icon in the tray to stop animating and re-run.

**"denied: permission_denied: read_package" on pull**
Your GHCR images are private. Either make them public (GitHub → your profile → Packages → each package → Package settings → Change visibility → Public), OR run once:
```powershell
$env:GHCR_PAT="ghp_YOUR_CLASSIC_TOKEN_WITH_read:packages"
$env:GHCR_PAT | docker login ghcr.io -u <your-username> --password-stdin
```

**Staff computers can't reach `http://<server-ip>:8080`**
- Make sure they're on the **same WiFi/LAN** as the server
- Windows Firewall on the server might have blocked port 8080. Re-run `setup.ps1` as Administrator, or open PowerShell as Admin and:
  ```powershell
  New-NetFirewallRule -DisplayName 'Narrative.Rx (TCP 8080)' -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Any
  ```
- Check the IP hasn't changed: `ipconfig` on the server

**"Address already in use" — port 8080 is taken**
Edit `.env` and change `WEB_PORT=8080` to e.g. `8090`, then run `windows\start.bat`. Also update the CORS line to match.

**Backups**
Run `windows\backup.bat` whenever you want a snapshot. Copy the resulting `.gz` file to a USB drive, network share, or OneDrive folder for safekeeping. Restore with:
```powershell
docker exec -i narrative-rx-mongo mongorestore --archive --gzip --db narrative_rx < windows\backups\narrative_rx_2026-02-14_1830.gz
```

**Everything stopped working — how do I fully restart?**
```powershell
cd C:\narrative-rx
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml down
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

---

## Uninstall

```powershell
cd C:\narrative-rx
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml down -v   # -v also deletes the MongoDB volume — data is gone
cd C:\
Remove-Item -Recurse -Force C:\narrative-rx
```

Uninstall Docker Desktop from Windows **Settings → Apps** if you don't want it anymore.
