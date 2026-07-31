# Narrative.Rx macOS installer (.pkg)

Ships a native macOS `.pkg` for Apple Silicon (M1/M2/M3) Macs running macOS 12+.

## What it installs

| Layout | Path |
|---|---|
| App root | `/Library/Application Support/NarrativeRx/` |
| Config (.env) | `/Library/Application Support/NarrativeRx/.env` |
| Logs | `/Library/Logs/NarrativeRx/` |
| Backend service (launchd) | `/Library/LaunchDaemons/com.narrativerx.app.plist` |
| MongoDB service (launchd) | `/Library/LaunchDaemons/com.narrativerx.mongodb.plist` |
| Re-runnable settings wizard | `/Library/Application Support/NarrativeRx/mac/firstrun.command` |

## postinstall summary

`scripts/postinstall` runs as root after the .pkg extracts. It:
1. Detects the console user and shells out via `sudo -u <user>` for Homebrew
   (Homebrew refuses to run as root).
2. Installs Homebrew if missing.
3. `brew install python@3.12 mongodb-community` (skipped if already present).
4. Creates the Python venv at `.../backend/.venv/` and installs `requirements.txt`.
5. Seeds `.env` with defaults + random JWT_SECRET.
6. Loads the two launchd services.
7. Waits for `http://localhost:8080` to come up, then opens Terminal at the
   first-run wizard so the user can paste their Emergent LLM key.

## Building the .pkg locally (on a Mac)

```bash
cd Narrative-2
./installer/mac/build-pkg.sh 1.0.0
# → installer/dist/NarrativeRx-Setup-1.0.0.pkg
```

Prerequisites:
- Apple Silicon Mac running macOS 12+
- Node 20 + Yarn (for `yarn build` in `frontend/`)
- Python 3.12
- `pkgbuild` and `productbuild` (ship with Xcode Command Line Tools)

## Code signing (not enabled yet)

The `.pkg` is unsigned. First-time users will get:

> "NarrativeRx-Setup-1.0.0.pkg" cannot be opened because it is from an
> unidentified developer.

Workaround: **Right-click the .pkg → Open**, then click **Open** in the dialog.
Only needed once per download.

To sign later (requires Apple Developer Program membership, $99/yr):
1. Add `--sign "Developer ID Installer: Your Name (TEAMID)"` to the `productbuild`
   call in `build-pkg.sh`.
2. Store the certificate in the CI runner's keychain via a secret + `security import`.
3. Notarize with `xcrun notarytool submit --wait ... `.
4. Staple with `xcrun stapler staple`.

## Uninstall

There is no `.pkg` uninstaller by default. To remove:
```bash
sudo launchctl unload /Library/LaunchDaemons/com.narrativerx.app.plist
sudo launchctl unload /Library/LaunchDaemons/com.narrativerx.mongodb.plist
sudo rm -f /Library/LaunchDaemons/com.narrativerx.app.plist
sudo rm -f /Library/LaunchDaemons/com.narrativerx.mongodb.plist
sudo rm -rf "/Library/Application Support/NarrativeRx"
sudo rm -rf /Library/Logs/NarrativeRx
# Optional: remove MongoDB + Python
brew uninstall mongodb-community python@3.12
```

## Files in this folder

| File | Purpose |
|---|---|
| `build-pkg.sh` | Assembles payload + runs `pkgbuild`/`productbuild` |
| `firstrun.command` | Terminal-based settings wizard shown on first launch |
| `updater.sh` | Downloads the newest .pkg and re-installs (used by in-app updater) |
| `scripts/postinstall` | Runs at the end of the .pkg install (see above) |
| `launchd/com.narrativerx.app.plist` | Backend service definition |
| `launchd/com.narrativerx.mongodb.plist` | MongoDB service definition |
