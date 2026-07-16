"""
Narrative generation service using Claude Sonnet 4.5 via Emergent LLM Key.
Supports carrier-specific tuning, section-level regeneration, and denial-appeal letters.
Includes a shared semaphore to cap concurrent LLM calls.
"""

import os
import json
import re
import uuid
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage


# Cap concurrent Claude calls across the process (bulk visit + appeal)
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


BASE_SYSTEM = """You are a senior dental insurance biller writing claim narratives for a US dental office.
Your narratives justify medical necessity to third-party carriers using accurate clinical terminology.

Rules:
- Never fabricate clinical findings the user did not provide. If a detail is missing, use conservative, neutral language.
- Use precise dental terminology (e.g., "non-restorable caries", "vertical root fracture", "periapical radiolucency", "furcation involvement", "class II mobility", "5-7mm probing depths").
- Reference CDT codes when helpful.
- Never mention the patient's name, DOB, or PHI unless provided.
- Do not include disclaimers, apologies, greetings, sign-offs, or "Dear Adjudicator" style openings.
- Write in third person, past tense for completed procedures.
- Output MUST be a single JSON object. No prose outside JSON. No markdown fences."""


APPEAL_SYSTEM = """You are a senior dental insurance appeals specialist writing a FORMAL appeal letter to an insurance carrier that denied a claim.

Rules:
- Write a real letter (200-350 words) with clear structure: date placeholder, carrier address placeholder, Re: line with CDT code + tooth + DOS, salutation ("Dear Claims Reviewer,"), 2-4 body paragraphs, closing ("Respectfully,"), signature line.
- Address the specific denial reason DIRECTLY. Refute or clarify with the clinical facts from the provided narrative.
- Cite the clinical, radiographic, and periodontal findings that establish medical necessity.
- Do NOT invent new clinical facts. Only use information provided in the narrative and appeal context.
- Include one clear "we respectfully request reconsideration of this claim" statement.
- Never use PHI unless provided in inputs.
- Output MUST be a single JSON object. No prose outside JSON. No markdown fences.

Output schema:
{
  "subject_line": "<one-line Re: subject, e.g. 'Appeal — CDT D3330 endodontic therapy, tooth #30, DOS 2026-01-15'>",
  "letter": "<full letter text with newlines between paragraphs. Use [Office Name], [Carrier Address], [Claim #] and [Date] as bracketed placeholders where the biller will fill in.>"
}"""


def _system_prompt(carrier: str | None = None, schema: str = "both") -> str:
    carrier_key = (carrier or "generic").lower()
    guidance = CARRIER_GUIDANCE.get(carrier_key, CARRIER_GUIDANCE["generic"])
    schema_text = ""
    if schema == "short":
        schema_text = '{ "short_narrative": "<1-2 sentences, ~25-45 words, suitable for the claim form Remarks field>" }'
    elif schema == "long":
        schema_text = '{ "long_narrative": "<3-6 sentences, ~80-160 words, suitable for a claim attachment or appeal letter>" }'
    else:
        schema_text = (
            '{\n'
            '  "short_narrative": "<1-2 sentences, ~25-45 words, suitable for the claim form Remarks field>",\n'
            '  "long_narrative": "<3-6 sentences, ~80-160 words, suitable for a claim attachment or appeal letter>"\n'
            '}'
        )
    return f"{BASE_SYSTEM}\n\nCarrier guidance: {guidance}\n\nOutput schema:\n{schema_text}"


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


def _new_chat(system_message: str) -> LlmChat:
    return LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"dental-{uuid.uuid4()}",
        system_message=system_message,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")


async def generate_narrative(payload: dict, procedure: dict) -> dict:
    async with LLM_SEMAPHORE:
        chat = _new_chat(_system_prompt(payload.get("carrier"), schema="both"))
        lines = _clinical_lines(payload, procedure)
        lines.append("")
        lines.append("Generate the short and long narrative JSON now.")
        response_text = await chat.send_message(UserMessage(text="\n".join(lines)))
    data = _extract_json(response_text)
    return {
        "short_narrative": data.get("short_narrative", "").strip(),
        "long_narrative": data.get("long_narrative", "").strip(),
    }


async def regenerate_field(field: str, payload: dict, procedure: dict) -> str:
    if field not in ("short", "long"):
        raise ValueError("field must be 'short' or 'long'")
    async with LLM_SEMAPHORE:
        chat = _new_chat(_system_prompt(payload.get("carrier"), schema=field))
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
                                 office_name: str = "[Office Name]") -> dict:
    """Generate a formal appeal letter referencing an existing narrative and denial info."""
    lines = [
        f"ORIGINAL NARRATIVE PROCEDURE: {narrative.get('procedure_name', '')} (CDT {narrative.get('procedure_code', '')})",
        f"Tooth: {narrative.get('tooth_number') or 'N/A'}",
        f"Carrier: {(narrative.get('carrier') or 'generic').title()}",
        f"Date of service: {narrative.get('inputs', {}).get('date_of_service') or 'N/A'}",
        f"Office name: {office_name}",
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
    lines.append("")
    lines.append("Generate the appeal letter JSON now.")
    async with LLM_SEMAPHORE:
        chat = _new_chat(APPEAL_SYSTEM)
        response_text = await chat.send_message(UserMessage(text="\n".join(lines)))
    data = _extract_json(response_text)
    return {
        "subject_line": (data.get("subject_line") or "").strip(),
        "letter": (data.get("letter") or "").strip(),
    }
