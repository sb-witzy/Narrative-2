"""
Narrative generation service using Claude Sonnet 4.5 via Emergent LLM Key.
Supports carrier-specific tuning and section-level regeneration.
"""

import os
import json
import re
import uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage


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


def _system_prompt(carrier: str | None = None, schema: str = "both") -> str:
    carrier_key = (carrier or "generic").lower()
    guidance = CARRIER_GUIDANCE.get(carrier_key, CARRIER_GUIDANCE["generic"])
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
    if payload.get("tooth_number"):
        lines.append(f"Tooth number: #{payload['tooth_number']}")
    if payload.get("surfaces"):
        lines.append(f"Surfaces involved: {payload['surfaces']}")
    if payload.get("symptoms"):
        lines.append(f"Patient-reported symptoms: {payload['symptoms']}")
    if payload.get("clinical_findings"):
        lines.append(f"Clinical findings: {payload['clinical_findings']}")
    if payload.get("radiographic_findings"):
        lines.append(f"Radiographic findings: {payload['radiographic_findings']}")
    if payload.get("pulp_status"):
        lines.append(f"Pulp status: {payload['pulp_status']}")
    if payload.get("perio_findings"):
        lines.append(f"Periodontal findings: {payload['perio_findings']}")
    if payload.get("prior_treatment"):
        lines.append(f"Prior treatment: {payload['prior_treatment']}")
    if payload.get("date_of_service"):
        lines.append(f"Date of service: {payload['date_of_service']}")
    if payload.get("visit_notes"):
        lines.append(f"Shared visit context: {payload['visit_notes']}")
    if payload.get("additional_notes"):
        lines.append(f"Additional notes: {payload['additional_notes']}")
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
        session_id=f"dental-narr-{uuid.uuid4()}",
        system_message=system_message,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")


async def generate_narrative(payload: dict, procedure: dict) -> dict:
    """Generate both short and long narrative."""
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
    """Regenerate only 'short' or 'long' narrative."""
    if field not in ("short", "long"):
        raise ValueError("field must be 'short' or 'long'")
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
