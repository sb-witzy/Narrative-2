# Narrative.Rx Windows installer

This folder contains the Inno Setup script and payload assembly used to
build **`NarrativeRx-Setup-<version>.exe`** — a single-file installer that
other dental offices can download and run to install Narrative.Rx on
their own Windows Server or Windows 10/11 workstation.

## What the installer does

1. Prompts the user for their **Emergent LLM key** and a **practice activation key**
2. Silently installs **MongoDB Community 7** as a Windows Service (skipped if already present)
3. Copies the app to `C:\Program Files\Narrative.Rx\`
4. Writes the config file to `C:\ProgramData\NarrativeRx\.env`
5. Opens **Windows Firewall inbound TCP 8080**
6. Registers **`NarrativeRxApp`** as a Windows Service (auto-start, depends on MongoDB)
7. Creates Desktop + Start Menu shortcuts
8. Registers a proper uninstaller in **Add or Remove Programs**

## How to trigger a build

Tag a commit and push:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions (see `.github/workflows/build-installer.yml`) will:
- Build the frontend with `yarn build`
- Create the backend venv and install all Python deps
- Download NSSM and MongoDB Community MSI
- Compile the installer with Inno Setup
- Attach `NarrativeRx-Setup-1.0.0.exe` to the **GitHub Release** page for that tag

Users then download from:
`https://github.com/YOUR-USERNAME/narrative-rx/releases/latest`

## Building locally (optional)

Only needed if you want to test installer changes before pushing:

1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php)
2. Manually assemble `installer\payload\` following the same steps as the CI workflow
3. Right-click `NarrativeRx.iss` → Compile
4. Output goes to `installer\dist\`

## Files in this folder

| File | Purpose |
|---|---|
| `NarrativeRx.iss` | Inno Setup script — the recipe for the installer |
| `EULA.txt` | End-user license agreement shown during install |
| `payload-static/open-narrative-rx.bat` | Launcher used by desktop/Start Menu shortcut |
| `payload/` (git-ignored) | Assembled during CI — do not commit |
| `dist/` (git-ignored) | Compiled `.exe` output |

## What still needs to be done (Phase 3+)

- Publisher name in `NarrativeRx.iss` currently reads `"Narrative.Rx"` — replace with your registered publisher name if you have one
- `AppURL` currently points to `YOUR-USERNAME/narrative-rx` — update to your actual GitHub org/repo
- Activation key validation logic (currently accepts any string) — will be added in the next phase
- In-app auto-updater — not included in this phase (users download new .exe manually)
