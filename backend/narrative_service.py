"""
Narrative generation service using Claude via Emergent LLM Key.
- Streaming (SSE) for narratives + appeal letters via `stream_message`.
- Kept non-streaming versions for bulk-visit (parallel batch) and back-compat.
- Appeal generation uses prior winning-appeal excerpts as few-shot examples
  when available for the same (carrier, procedure_code).
"""

import os
import json
import re
import uuid
import asyncio
from typing import AsyncGenerator, Optional
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone


# Cap concurrent Claude calls across the process
_MAX_CONCURRENT_LLM = int(os.environ.get("MAX_CONCURRENT_LLM", "3"))
LLM_SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT_LLM)


CARRIER_GUIDANCE = {
    "generic": "Neutral, universal language accepted by most carriers.",
    "delta": "Delta Dental prefers concise, evidence-focused language. Explicitly reference CDT nomenclature, cite pocket depths / bone loss / caries depth in millimeters, and avoid emotional or subjective phrasing.",
    "cigna": "Cigna adjudicators respond to structured clinical reasoning. Lead with objective findings, then diagnosis, then treatment justification. Reference least-costly-alternative language when applicable.",
    "metlife": "MetLife favors thorough documentation of prior treatment and failure history. Explicitly state date/reason of any prior restoration failure or endodontic outcome.",
    "aetna": "Aetna requires clear medical necessity statements. State why less-invasive alternatives were considered and ruled out.",
    "bcbs": "BCBS local plans vary; write to the strictest interpretation. Include specific quantitative findings (mm of bone loss, radiographic evidence description) and reference clinical guidelines when relevant.",
}


# --------------- Prompt bases ---------------

_BASE_RULES = """You are a senior dental insurance biller writing claim narratives for a US dental office.
Your narratives justify medical necessity to third-party carriers using accurate clinical terminology.

Rules:
- Never fabricate clinical findings the user did not provide. If a detail is missing, use conservative, neutral language.
- Use precise dental terminology (e.g., "non-restorable caries", "vertical root fracture", "periapical radiolucency", "furcation involvement", "class II mobility", "5-7mm probing depths").
- Reference CDT codes when helpful.
- Never mention the patient's name, DOB, or PHI unless provided.
- Do not include disclaimers, apologies, greetings, sign-offs, or "Dear Adjudicator" style openings.
- Write in third person, past tense for completed procedures."""

# Streaming output format for narratives — text between marker tags,
# parseable incrementally on the frontend.
_NARR_STREAM_FORMAT = """Output format (STRICT — no other text, no JSON, no markdown fences):
[SHORT]
<one or two sentences, ~25-45 words, for the claim form Remarks field>
[/SHORT]
[LONG]
<three to six sentences, ~80-160 words, for a claim attachment or appeal>
[/LONG]"""

# JSON output format kept for the non-streaming batch path (bulk visit)
_NARR_JSON_FORMAT = """Output MUST be a single JSON object. No prose outside JSON. No markdown fences.

Output schema:
{
  "short_narrative": "<1-2 sentences, ~25-45 words, suitable for the claim form Remarks field>",
  "long_narrative": "<3-6 sentences, ~80-160 words, suitable for a claim attachment or appeal letter>"
}"""

_APPEAL_STREAM_FORMAT = """Output format (STRICT — no other text, no JSON, no markdown fences):
[SUBJECT]
<one-line Re: subject, e.g. "Appeal - CDT D3330 endodontic therapy, tooth #30, DOS 2026-01-15">
[/SUBJECT]
[LETTER]
<full letter (200-350 words) with newlines between paragraphs. Use [Office Name], [Carrier Address], [Claim #] and [Date] as bracketed placeholders where the biller will fill in.>
[/LETTER]"""

_APPEAL_JSON_FORMAT = """Output MUST be a single JSON object. No prose outside JSON. No markdown fences.

Output schema:
{
  "subject_line": "<one-line Re: subject>",
  "letter": "<full letter text with newlines between paragraphs>"
}"""

_APPEAL_RULES = """You are a senior dental insurance appeals specialist writing a FORMAL appeal letter to an insurance carrier that denied a claim.

Rules:
- Write a real letter (200-350 words) with clear structure: date placeholder, carrier address placeholder, Re: line with CDT code + tooth + DOS, salutation ("Dear Claims Reviewer,"), 2-4 body paragraphs, closing ("Respectfully,"), signature line.
- Address the specific denial reason DIRECTLY. Refute or clarify with the clinical facts from the provided narrative.
- Cite the clinical, radiographic, and periodontal findings that establish medical necessity.
- Do NOT invent new clinical facts. Only use information provided in the narrative and appeal context.
- Include one clear "we respectfully request reconsideration of this claim" statement.
- Never use PHI unless provided in inputs."""


# --------------- Prompt builders ---------------

def _narr_system(carrier: Optional[str], streaming: bool = True, schema: str = "both") -> str:
    carrier_key = (carrier or "generic").lower()
    guidance = CARRIER_GUIDANCE.get(carrier_key, CARRIER_GUIDANCE["generic"])
    if streaming:
        fmt = _NARR_STREAM_FORMAT
        if schema == "short":
            fmt = "Output only the [SHORT]...[/SHORT] block. No [LONG] block."
        elif schema == "long":
            fmt = "Output only the [LONG]...[/LONG] block. No [SHORT] block."
    else:
        if schema == "short":
            fmt = 'Output MUST be a single JSON object: { "short_narrative": "..." }'
        elif schema == "long":
            fmt = 'Output MUST be a single JSON object: { "long_narrative": "..." }'
        else:
            fmt = _NARR_JSON_FORMAT
    return f"{_BASE_RULES}\n\nCarrier guidance: {guidance}\n\n{fmt}"


def _appeal_system(streaming: bool, prior_wins: Optional[list] = None) -> str:
    fmt = _APPEAL_STREAM_FORMAT if streaming else _APPEAL_JSON_FORMAT
    few_shot = ""
    if prior_wins:
        pieces = []
        for i, w in enumerate(prior_wins[:2], start=1):
            excerpt = (w.get("letter") or "").strip()
            if len(excerpt) > 1200:
                excerpt = excerpt[:1200] + "..."
            pieces.append(f"WINNING EXAMPLE #{i} (carrier accepted this appeal):\n{excerpt}")
        few_shot = (
            "\n\nPRIOR WINNING APPEALS from this office for the same carrier / procedure - "
            "mirror their tone, structure, and argument style, but adapt fully to the CURRENT case's clinical facts:\n\n"
            + "\n\n---\n\n".join(pieces)
        )
    return f"{_APPEAL_RULES}{few_shot}\n\n{fmt}"


def _clinical_lines(payload: dict, procedure: dict) -> list[str]:
    lines = [
        f"Procedure: {procedure['name']} (CDT {procedure['code']})",
        f"Category: {procedure['category']}",
    ]
    for label, key in [
        ("Tooth number", "tooth_number"),
        ("Surfaces involved", "surfaces"),
        ("Patient-reported symptoms", "symptoms"),
        ("Clinical findings", "clinical_findings"),
        ("Radiographic findings", "radiographic_findings"),
        ("Pulp status", "pulp_status"),
        ("Periodontal findings", "perio_findings"),
        ("Prior treatment", "prior_treatment"),
        ("Date of service", "date_of_service"),
        ("Shared visit context", "visit_notes"),
        ("Additional notes", "additional_notes"),
    ]:
        if payload.get(key):
            lines.append(f"{label}: {payload[key]}")
    return lines


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]}")
    return json.loads(match.group(0))


def _new_chat(system_message: str, model: str) -> LlmChat:
    return LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"dental-{uuid.uuid4()}",
        system_message=system_message,
    ).with_model("anthropic", model)


NARRATIVE_MODEL = "claude-haiku-4-5-20251001"
APPEAL_MODEL = "claude-sonnet-4-5-20250929"


# --------------- Non-streaming (batch / bulk) ---------------

async def generate_narrative(payload: dict, procedure: dict) -> dict:
    async with LLM_SEMAPHORE:
        chat = _new_chat(_narr_system(payload.get("carrier"), streaming=False, schema="both"), model=NARRATIVE_MODEL)
        lines = _clinical_lines(payload, procedure)
        lines.append("")
        lines.append("Generate the short and long narrative JSON now.")
        response_text = await chat.send_message(UserMessage(text="\n".join(lines)))
    data = _extract_json(response_text)
    return {
        "short_narrative": (data.get("short_narrative") or "").strip(),
        "long_narrative": (data.get("long_narrative") or "").strip(),
    }


async def regenerate_field(field: str, payload: dict, procedure: dict) -> str:
    if field not in ("short", "long"):
        raise ValueError("field must be 'short' or 'long'")
    async with LLM_SEMAPHORE:
        chat = _new_chat(_narr_system(payload.get("carrier"), streaming=False, schema=field), model=NARRATIVE_MODEL)
        lines = _clinical_lines(payload, procedure)
        if payload.get("existing_short") and field == "long":
            lines.append(f"Existing short narrative (for consistency): {payload['existing_short']}")
        if payload.get("existing_long") and field == "short":
            lines.append(f"Existing long narrative (for consistency): {payload['existing_long']}")
        lines.append("")
        lines.append(f"Regenerate ONLY the {field}_narrative field. Return JSON with a single key.")
        response_text = await chat.send_message(UserMessage(text="\n".join(lines)))
    data = _extract_json(response_text)
    key = f"{field}_narrative"
    return (data.get(key) or "").strip()


async def generate_appeal_letter(narrative: dict, denial_reason: str,
                                 denial_code: str = "", extra_context: str = "",
                                 office_name: str = "[Office Name]",
                                 practice: Optional[dict] = None,
                                 prior_wins: Optional[list] = None) -> dict:
    lines = _appeal_user_lines(narrative, denial_reason, denial_code, extra_context, office_name, practice)
    lines.append("")
    lines.append("Generate the appeal letter JSON now.")
    async with LLM_SEMAPHORE:
        chat = _new_chat(_appeal_system(streaming=False, prior_wins=prior_wins), model=APPEAL_MODEL)
        response_text = await chat.send_message(UserMessage(text="\n".join(lines)))
    data = _extract_json(response_text)
    return {
        "subject_line": (data.get("subject_line") or "").strip(),
        "letter": (data.get("letter") or "").strip(),
    }


def _appeal_user_lines(narrative: dict, denial_reason: str, denial_code: str,
                       extra_context: str, office_name: str, practice: Optional[dict]) -> list[str]:
    lines = [
        f"ORIGINAL NARRATIVE PROCEDURE: {narrative.get('procedure_name', '')} (CDT {narrative.get('procedure_code', '')})",
        f"Tooth: {narrative.get('tooth_number') or 'N/A'}",
        f"Carrier: {(narrative.get('carrier') or 'generic').title()}",
        f"Date of service: {narrative.get('inputs', {}).get('date_of_service') or 'N/A'}",
        f"Office name: {office_name}",
    ]
    if practice:
        addr_bits = [practice.get(k) for k in ("address_line1", "address_line2", "city", "state", "zip_code") if practice.get(k)]
        if addr_bits:
            lines.append(f"Office address: {', '.join(addr_bits)}")
        if practice.get("phone"): lines.append(f"Office phone: {practice['phone']}")
        if practice.get("npi"): lines.append(f"Office NPI: {practice['npi']}")
        if practice.get("provider_name"):
            p = practice["provider_name"]
            if practice.get("provider_license"): p += f", Lic #{practice['provider_license']}"
            lines.append(f"Treating provider: {p}")
    lines += [
        "",
        "SHORT NARRATIVE (submitted originally):",
        narrative.get("short_narrative", ""),
        "",
        "LONG NARRATIVE (submitted originally):",
        narrative.get("long_narrative", ""),
        "",
        "DENIAL REASON PROVIDED BY CARRIER:",
        denial_reason,
    ]
    if denial_code:
        lines.append(f"Denial code: {denial_code}")
    if extra_context:
        lines.append("")
        lines.append(f"ADDITIONAL APPEAL CONTEXT: {extra_context}")
    return lines


# --------------- Streaming ---------------

async def stream_narrative(payload: dict, procedure: dict) -> AsyncGenerator[str, None]:
    """Stream marker-tagged narrative text: [SHORT]...[/SHORT][LONG]...[/LONG]"""
    async with LLM_SEMAPHORE:
        chat = _new_chat(_narr_system(payload.get("carrier"), streaming=True, schema="both"), model=NARRATIVE_MODEL)
        lines = _clinical_lines(payload, procedure)
        lines.append("")
        lines.append("Generate the narrative NOW using the [SHORT]/[LONG] format above.")
        async for ev in chat.stream_message(UserMessage(text="\n".join(lines))):
            if isinstance(ev, TextDelta):
                yield ev.content
            elif isinstance(ev, StreamDone):
                return


async def stream_regenerate_field(field: str, payload: dict, procedure: dict) -> AsyncGenerator[str, None]:
    """Stream a single regenerated section, tagged [SHORT] or [LONG]."""
    if field not in ("short", "long"):
        raise ValueError("field must be 'short' or 'long'")
    async with LLM_SEMAPHORE:
        chat = _new_chat(_narr_system(payload.get("carrier"), streaming=True, schema=field), model=NARRATIVE_MODEL)
        lines = _clinical_lines(payload, procedure)
        if payload.get("existing_short") and field == "long":
            lines.append(f"Existing short narrative (for consistency): {payload['existing_short']}")
        if payload.get("existing_long") and field == "short":
            lines.append(f"Existing long narrative (for consistency): {payload['existing_long']}")
        lines.append("")
        lines.append(f"Regenerate ONLY the {field} narrative using the [{field.upper()}]/[/{field.upper()}] format.")
        async for ev in chat.stream_message(UserMessage(text="\n".join(lines))):
            if isinstance(ev, TextDelta):
                yield ev.content
            elif isinstance(ev, StreamDone):
                return


async def stream_appeal_letter(narrative: dict, denial_reason: str,
                                denial_code: str = "", extra_context: str = "",
                                office_name: str = "[Office Name]",
                                practice: Optional[dict] = None,
                                prior_wins: Optional[list] = None) -> AsyncGenerator[str, None]:
    """Stream marker-tagged appeal: [SUBJECT]...[/SUBJECT][LETTER]...[/LETTER]"""
    lines = _appeal_user_lines(narrative, denial_reason, denial_code, extra_context, office_name, practice)
    lines.append("")
    lines.append("Generate the appeal NOW using the [SUBJECT]/[LETTER] format above.")
    async with LLM_SEMAPHORE:
        chat = _new_chat(_appeal_system(streaming=True, prior_wins=prior_wins), model=APPEAL_MODEL)
        async for ev in chat.stream_message(UserMessage(text="\n".join(lines))):
            if isinstance(ev, TextDelta):
                yield ev.content
            elif isinstance(ev, StreamDone):
                return


# --------------- Marker parsing (for server-side final capture) ---------------

_TAG_RE = re.compile(r"\[(/?)(SHORT|LONG|SUBJECT|LETTER)\]", re.IGNORECASE)


def parse_marker_text(text: str) -> dict:
    """Extract sections from streamed marker-tagged text. Robust to whitespace, missing close tags."""
    out = {"short_narrative": "", "long_narrative": "", "subject_line": "", "letter": ""}
    field_map = {
        "SHORT": "short_narrative",
        "LONG": "long_narrative",
        "SUBJECT": "subject_line",
        "LETTER": "letter",
    }
    current = None
    pos = 0
    buffer = []
    for m in _TAG_RE.finditer(text):
        chunk = text[pos:m.start()]
        if current:
            buffer.append(chunk)
        pos = m.end()
        closing, name = m.group(1), m.group(2).upper()
        if closing:
            if current and field_map.get(current):
                out[field_map[current]] = "".join(buffer).strip()
            current = None
            buffer = []
        else:
            current = name
            buffer = []
    # tail: unclosed section
    if current and field_map.get(current):
        out[field_map[current]] = (out[field_map[current]] + "".join(buffer) + text[pos:]).strip()
    return out
