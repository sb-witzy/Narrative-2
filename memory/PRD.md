# Narrative.Rx — Dental Claim Narrative Assistant

## Problem Statement
Build a program that assists a dental office with insurance narrative writeups. Provides both short and long narratives to accompany claim submissions, allows copy-and-paste, and advises on radiograph requirements.

## User Choices
- **Narrative generation:** AI-based (Claude Sonnet 4.5 via Emergent LLM Universal Key)
- **Procedures:** All common (crowns, endo, extractions, perio, implants, grafts, guards, bridges) — 22 CDT codes seeded
- **History:** Save every generated narrative to MongoDB
- **Authentication:** None (single-office intended use)

## Architecture
- **Backend:** FastAPI (`/app/backend/server.py`) + Motor/Mongo + `emergentintegrations` LlmChat → `anthropic/claude-sonnet-4-5-20250929`
- **Frontend:** React 19 + Tailwind + Shadcn UI, `Manrope` display / `IBM Plex Sans` body, sage-green (#4A6B5D) accent, neumorphic "clay" cards
- **Data model:** `narratives` collection with id (uuid str), procedure_code, procedure_name, tooth_number, patient_label (no PHI), short_narrative, long_narrative, radiographs, inputs, created_at (ISO str)

## Core API
- `GET /api/procedures` — catalog of 22 CDT procedures with radiograph metadata
- `POST /api/generate` — generate + save narrative
- `GET /api/history`, `GET /api/history/{id}`, `DELETE /api/history/{id}`

## What's Been Implemented (2026-02)
### Iteration 1
- CDT procedure catalog with per-procedure radiograph advisor
- AI narrative generation (short + long) in claim-appropriate clinical language
- Dashboard with procedure grouping, clinical detail form, live radiograph panel, copy-to-clipboard
- History page with search, dialog viewer, delete

### Iteration 2 (all previously P1/P2 items shipped)
- **PDF & text export** for single narratives and full visit packets (`reportlab`-generated, one-file download)
- **Multi-procedure visit generator** at `/bulk` — one patient, one carrier, one visit, N procedures, parallel LLM calls, single packet export
- **Carrier-specific templates** for Generic / Delta / Cigna / MetLife / Aetna / BCBS (carrier field tunes the system prompt)
- **Editable narratives + section-level regenerate** — inline textarea edit with autosave (PATCH) and per-field regenerate button
- **Tooth-diagram picker** using Universal Numbering (adult 1–32 + primary A–T) with single or multi-select

## Prioritized Backlog (P0 → P2)
- **P2:** Cap concurrent LLM calls in bulk-visit generation (currently N-parallel)
- **P2:** Robust JSON extraction from LLM (nested-brace resilient) or tool-format output
- **P2:** Office branding: real logo + office name on exported PDFs (env-driven)
- **P2:** Optional lightweight auth for multi-office/multi-user use
- **P3:** Attach radiograph filenames/uploads to a record for full "claim packet" tracking
- **P3:** Denial-appeal-letter generator (uses existing narrative + carrier denial reason)

## Next Tasks
- Gather user feedback on generated narrative tone (formal vs conversational) and adjust system prompt if needed
- Decide on export format (PDF, .docx, or plain text)
