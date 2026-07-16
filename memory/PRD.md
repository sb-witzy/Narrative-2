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
- CDT procedure catalog with per-procedure radiograph advisor (Required / Recommended / Note)
- AI narrative generation returning structured JSON (short + long) with claim-appropriate clinical language
- Dashboard with procedure grouping, clinical detail form, live radiograph panel, copy-to-clipboard with toast + flash animation
- History page with search, dialog viewer, delete, and copy buttons
- No PHI stored — patient_label field is a free-form non-identifying tag

## Prioritized Backlog (P0 → P2)
- **P1:** PDF/text export of a narrative bundle for attaching to claim submissions
- **P1:** Bulk-mode narrative generator for multiple procedures on the same visit
- **P1:** Carrier-specific templates (Delta, Cigna, MetLife, BCBS) — different length/format preferences
- **P2:** Editable narrative before saving (regenerate section only)
- **P2:** Optional lightweight auth if multi-office/multi-user is needed later
- **P2:** Tooth-diagram visual picker instead of free-text tooth number
- **P2:** Attach radiograph filenames to a record for full "claim packet" tracking

## Next Tasks
- Gather user feedback on generated narrative tone (formal vs conversational) and adjust system prompt if needed
- Decide on export format (PDF, .docx, or plain text)
