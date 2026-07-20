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

## Tech stack
- Backend: FastAPI, MongoDB (Motor), emergentintegrations (Claude Haiku 4.5 for narratives, Claude Sonnet 4.5 for appeals), ReportLab, PyJWT, bcrypt
- Frontend: React 18, Tailwind, shadcn/ui, sonner, lucide-react, axios
- Infra: NSSM (Windows Service wrapper), native MongoDB service, Windows Firewall rule on 8080
- Auto-start on boot via SERVICE_AUTO_START + MongoDB dependency

## Files of note
- `/app/backend/narrative_service.py` — streaming + non-streaming LLM generation
- `/app/backend/server.py` — API routes including SSE endpoints
- `/app/backend/pdf_service.py` — PDF gen with logo header
- `/app/frontend/src/lib/api.js` — axios client + streamSSE + makeMarkerParser
- `/app/frontend/src/components/AppealDialog.jsx` — streaming + outcome UI
- `/app/frontend/src/pages/Dashboard.jsx` — streaming narrative UI
- `/app/windows/setup.ps1` — native Windows Server installer
- `/app/windows/create-desktop-shortcut.ps1` — per-staff-PC desktop icon installer

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
