# Narrative.Rx PRD

## Original problem
Dental office needs an AI-powered insurance narrative writer that produces both short and long narratives for claim submission, advises on radiographs, provides copy-paste, and supports appeals with denial handling.

## Deployment
Self-hosted native Windows Server install with:
- Python + FastAPI backend (uvicorn wrapped by NSSM as a Windows Service)
- React frontend (built and served same-origin from FastAPI)
- MongoDB Community as native Windows Service
- Serves the office LAN on TCP 8080
- Docker/WSL/Podman all attempted and rejected — final native install works

## Implemented (as of Iter 17)
- Full auth (JWT + refresh cookie + 30-day remember-me + brute force protection)
- Narrative generation: short + long, per-carrier tuned, tooth-picker, radiograph advice
- Bulk-visit workflow (parallel narrative generation for a multi-procedure visit)
- History with edit + delete + PDF/TXT export
- Denial appeal letters with subject line, edit, PDF/TXT export
- **Print button** and **Email button** (mailto) on both narratives and appeals
- **Practice Settings** — logo, address, NPI, tax ID, provider name; auto-populated in PDF headers
- **Branding** — Narrative.Rx logo everywhere: browser favicon, top nav, login/register, PDF headers, Windows shortcut icon, PWA manifest
- **Streaming (Iter 17)** — narrative + appeal letter tokens appear word-by-word via SSE (`/generate/stream`, `/regenerate/stream`, `/appeals/stream`)
- **Appeal outcome tracker + carrier memory (Iter 17)** — mark Won / Lost / Pending; carrier + procedure patterns endpoint; prior winning appeals are auto-injected as few-shot examples when drafting new appeals for the same (carrier, procedure_code)
- **Windows .exe installer (Feb 2026)** — Inno Setup script + GitHub Actions workflow; `AppURL` wired to `sb-witzy/Narrative-2`; ready to tag `v1.0.0` for the first public installer release. See `/app/RELEASING.md`.
- **macOS .pkg installer (Feb 2026)** — Apple Silicon build via `pkgbuild`/`productbuild`; parallel GitHub Actions workflow `build-installer-mac.yml`; postinstall auto-installs Homebrew + python@3.12 + mongodb-community; launchd services for backend + MongoDB; Terminal-based first-run wizard.
- **First-run wizard (Feb 2026)** — Windows: `firstrun.py` Tkinter GUI compiled to `firstrun.exe` via PyInstaller, launched from Start Menu and on first launch if `.env` lacks `EMERGENT_LLM_KEY`. macOS: `firstrun.command` Terminal wizard. Both write `.env` and restart the service.
- **In-app auto-updater (Feb 2026)** — Settings → System → Check for updates queries GitHub Releases API directly (no `git` required). Backend picks `.exe` or `.pkg` asset based on platform, spawns `windows/exe-updater.bat` or `installer/mac/updater.sh` to download + re-install in place. Git-mode path preserved for dev / manual-clone installs.

## Tech stack
- Backend: FastAPI, MongoDB (Motor), emergentintegrations (Claude Haiku 4.5 for narratives, Claude Sonnet 4.5 for appeals), ReportLab, PyJWT, bcrypt
- Frontend: React 18, Tailwind, shadcn/ui, sonner, lucide-react, axios
- Infra: NSSM + native MongoDB service + Windows Firewall (Windows) · launchd + Homebrew mongodb-community (macOS)
- Auto-start on boot via `SERVICE_AUTO_START` + MongoDB dependency (Windows) / `RunAtLoad`+`KeepAlive` (macOS)

## Files of note
- `/app/backend/server.py` — API routes, SSE, and dual-mode auto-updater (git + installer)
- `/app/backend/narrative_service.py`, `pdf_service.py`
- `/app/frontend/src/pages/Settings.jsx` — System section (git + installer mode UI)
- `/app/installer/NarrativeRx.iss` — Inno Setup script
- `/app/installer/firstrun/firstrun.py` — Windows Tkinter wizard (→ `firstrun.exe`)
- `/app/installer/mac/build-pkg.sh` + `mac/scripts/postinstall` — macOS .pkg builder
- `/app/installer/mac/firstrun.command`, `mac/updater.sh`, `mac/launchd/*.plist`
- `/app/windows/exe-updater.bat` — installer-mode self-update
- `/app/.github/workflows/build-installer.yml` (Windows) + `build-installer-mac.yml` (Mac)
- `/app/backend/tests/backend_iter18_test.py` — installer detection + updater tests

## Backlog (P1)
- Nightly automatic backup via Windows Task Scheduler (~15 min)
- Off-site backup to OneDrive (~30 min)
- Uptime monitor + email alert (~1 hr)
- Log retention policy (~15 min)

## Backlog (P2)
- Keyboard shortcuts, save common clinical phrases, duplicate last narrative, better history search
- Expand carrier library to 20+ (currently 6)
- Chat-style refinement ("make it more concise")
- Analytics dashboard (win rate, top denials, time-saved counter)

## Backlog (P3 — only if HIPAA-scoped)
- Session auto-lock, MFA, PHI detector, field-level encryption, full audit log
