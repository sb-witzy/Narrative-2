"""
Narrative generation service using Claude Sonnet 4.5 via Emergent LLM Key.
Returns structured JSON with short_narrative and long_narrative.
"""

import os
import json
import re
import uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage


SYSTEM_PROMPT = """You are a senior dental insurance biller writing claim narratives for a US dental office.
Your narratives justify medical necessity to third-party insurance carriers (Delta, MetLife, Cigna, Aetna, BCBS, etc.) using accurate clinical terminology.

Rules:
- Never fabricate clinical findings the user did not provide. If a detail is missing, use conservative, neutral language.
- Use precise dental terminology (e.g., "non-restorable caries", "vertical root fracture", "periapical radiolucency", "furcation involvement", "class II mobility", "5-7mm probing depths").
- Reference CDT codes when helpful.
- Never mention the patient's name, DOB, or PHI unless provided.
- Do not include disclaimers, apologies, greetings, sign-offs, or "Dear Adjudicator" style openings.
- Write in third person, past tense for completed procedures, present tense for planned.
- Output MUST be a single JSON object. No prose outside JSON. No markdown fences.

Output schema:
{
  "short_narrative": "<1-2 sentences, ~25-45 words, suitable for the claim form 'Remarks' field>",
  "long_narrative": "<3-6 sentences, ~80-160 words, suitable for a claim attachment or appeal letter>"
}
"""


def _build_user_prompt(payload: dict, procedure: dict) -> str:
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
    if payload.get("additional_notes"):
        lines.append(f"Additional notes: {payload['additional_notes']}")

    lines.append("")
    lines.append("Generate the short and long narrative JSON now.")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    # Strip markdown code fences if present
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]}")
    return json.loads(match.group(0))


async def generate_narrative(payload: dict, procedure: dict) -> dict:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(
        api_key=api_key,
        session_id=f"dental-narr-{uuid.uuid4()}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    user_msg = UserMessage(text=_build_user_prompt(payload, procedure))
    response_text = await chat.send_message(user_msg)
    data = _extract_json(response_text)
    return {
        "short_narrative": data.get("short_narrative", "").strip(),
        "long_narrative": data.get("long_narrative", "").strip(),
    }
