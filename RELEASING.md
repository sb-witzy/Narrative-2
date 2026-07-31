# Releasing Narrative.Rx installers

Two GitHub Actions workflows produce the installers on every tag or manual dispatch:

| Workflow | Platform | Output |
|---|---|---|
| `.github/workflows/build-installer.yml` | Windows | `NarrativeRx-Setup-<version>.exe` |
| `.github/workflows/build-installer-mac.yml` | macOS (Apple Silicon) | `NarrativeRx-Setup-<version>.pkg` |

Both workflows attach their artifact to the same GitHub Release page.

---

## Option A — Tag push (recommended for real releases)

Run these commands **locally on your machine** after cloning
`https://github.com/sb-witzy/Narrative-2`:

```bash
git clone https://github.com/sb-witzy/Narrative-2.git
cd Narrative-2
git pull origin main
git tag v1.0.0
git push origin v1.0.0
```

Within ~15 minutes:
- Both Actions runs finish.
- `NarrativeRx-Setup-1.0.0.exe` **and** `NarrativeRx-Setup-1.0.0.pkg` are
  attached to https://github.com/sb-witzy/Narrative-2/releases/tag/v1.0.0
- Release notes are auto-generated.

For subsequent releases just bump the tag: `git tag v1.0.1`, `git push origin v1.0.1`.

---

## Option B — Manual dispatch (no local git needed)

- Windows: https://github.com/sb-witzy/Narrative-2/actions/workflows/build-installer.yml
- macOS:   https://github.com/sb-witzy/Narrative-2/actions/workflows/build-installer-mac.yml

Click **"Run workflow"** on each, enter the version (e.g. `1.0.0`), and click
**"Run workflow"**. Download artifacts from the finished run.

> Manual dispatch produces the installer as a workflow artifact but does
> **not** create a GitHub Release page. Use Option A for public releases.

---

## What each installer does

### Windows (`.exe`)
1. Prompts for Emergent LLM key + activation key.
2. Silently installs MongoDB Community 7 as a Windows Service (skipped if present).
3. Copies app to `C:\Program Files\Narrative.Rx\`.
4. Writes config to `C:\ProgramData\NarrativeRx\.env`.
5. Opens Windows Firewall inbound TCP 8080.
6. Registers **`NarrativeRxApp`** as a Windows Service (auto-start, MongoDB dependency).
7. Creates Desktop / Start Menu shortcuts (including **"Narrative.Rx Settings"** that
   re-runs the first-run wizard for key rotation).
8. Registers an uninstaller in Add or Remove Programs.

### macOS (`.pkg`)
1. Ensures Homebrew is installed (runs as the console user).
2. Installs `python@3.12` and `mongodb-community` if missing.
3. Copies app to `/Library/Application Support/NarrativeRx/`.
4. Creates the Python venv and installs backend deps.
5. Writes `.env` and generates a random JWT secret.
6. Installs launchd services (`com.narrativerx.app`, `com.narrativerx.mongodb`).
7. Opens a Terminal first-run wizard that collects the LLM key + admin creds.
8. Opens the app at http://localhost:8080 in the default browser.

**Note (macOS):** the .pkg is **not code-signed / notarized yet**. On first launch:
right-click the .pkg → **Open** to bypass Gatekeeper.

---

## In-app "Check for updates"

Once installed, the app polls **GitHub Releases** directly.

Settings → System → **Check for updates**:
- Detects installed version from the bundled `VERSION` file
- Compares to the latest GitHub Release tag
- **Install button** downloads the matching asset (`.exe` on Windows, `.pkg` on Mac)
  and re-runs it silently to upgrade in place

On a **git checkout** (developer install), the same button still uses `git pull`
+ rebuild instead — controlled automatically by the backend based on whether
`VERSION` file or `.git` directory is present.

---

## Verifying a build

- Actions: https://github.com/sb-witzy/Narrative-2/actions
- Latest release: https://github.com/sb-witzy/Narrative-2/releases/latest
- Approximate sizes: Windows `.exe` ~300 MB, macOS `.pkg` ~50 MB (Homebrew fetched at install time)

## If a build fails

Common causes:
- Python dependency not on PyPI mirror → check the "Create backend venv" step logs.
- Frontend `yarn build` failing → check the "Build frontend" step logs.
- Inno Setup / pkgbuild error → check the "Compile installer" / "Build .pkg" step logs.

Pinned versions:
- Python 3.12, Node 20
- MongoDB Community 7.0.14 (Windows) / brew tap (macOS)
- NSSM 2.24 (Windows) / launchd (macOS)
- Inno Setup 6 (Windows) / pkgbuild + productbuild (macOS)
- macOS runner: `macos-14` (Apple Silicon)
