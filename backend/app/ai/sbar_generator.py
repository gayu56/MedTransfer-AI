"""SBAR Clinical Summary Generator.

Generates SBAR (Situation-Background-Assessment-Recommendation) summaries
from structured patient data. Uses LLM when available, falls back to
template-based generation.
"""
import asyncio
import json
import re
from datetime import datetime, timezone

from app.config import settings
from app.models.patient import Patient
from app.models.clinical_summary import ClinicalSummary


def extract_json(text: str) -> dict | list | None:
    """Robustly extract JSON from LLM output that may contain markdown fences
    or surrounding prose.  Returns the parsed object or None."""
    if not text:
        return None
    text = text.strip()
    # 1. Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # 2. Extract from ```json ... ``` or ``` ... ``` fenced blocks
    fence_match = re.search(r"```(?:json)?\s*\n?(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass
    # Also check for fenced arrays
    fence_arr = re.search(r"```(?:json)?\s*\n?(\[.*?\])\s*```", text, re.DOTALL)
    if fence_arr:
        try:
            return json.loads(fence_arr.group(1))
        except (json.JSONDecodeError, TypeError):
            pass
    # 3. Find first { ... } or [ ... ] in the text (greedy)
    brace_match = re.search(r"(\{[\s\S]*\})", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass
    bracket_match = re.search(r"(\[[\s\S]*\])", text)
    if bracket_match:
        try:
            return json.loads(bracket_match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass
    return None


SBAR_SYSTEM_PROMPT = """You are a clinical documentation assistant generating SBAR transfer summaries.

RULES:
1. Use ONLY the patient data provided. NEVER fabricate clinical information.
2. Present vitals, labs, and medications EXACTLY as provided. Do not modify values.
3. If data is missing, state "Not available" — do NOT guess.
4. Use concise, professional clinical language.
5. The Recommendation section states transfer needs factually. Do NOT recommend treatments.

Generate a JSON object with keys: situation, background, assessment, recommendation"""

SBAR_USER_PROMPT = """Generate an SBAR transfer summary for:

PATIENT: {patient_name}, {age}{gender_char}, DOB: {dob}, MRN: {mrn}
REASON FOR TRANSFER: {reason}
URGENCY: {urgency}
REQUESTED SPECIALTY: {specialty}
SENDING FACILITY: Sending Medical Center

CLINICAL DATA:
{clinical_data}

ADDITIONAL CONTEXT: {additional_context}

Return a JSON object with keys: situation, background, assessment, recommendation"""


def _format_vitals(vitals: dict) -> str:
    if not vitals:
        return "Vitals: Not available"
    parts = []
    if vitals.get("bp_systolic") and vitals.get("bp_diastolic"):
        parts.append(f"BP: {vitals['bp_systolic']}/{vitals['bp_diastolic']} mmHg")
    if vitals.get("heart_rate"):
        parts.append(f"HR: {vitals['heart_rate']} bpm")
    if vitals.get("respiratory_rate"):
        parts.append(f"RR: {vitals['respiratory_rate']}")
    if vitals.get("spo2"):
        parts.append(f"SpO2: {vitals['spo2']}%")
    if vitals.get("temperature"):
        unit = vitals.get("temperature_unit", "F")
        parts.append(f"Temp: {vitals['temperature']}°{unit}")
    if vitals.get("pain_scale") is not None:
        parts.append(f"Pain: {vitals['pain_scale']}/10")
    if vitals.get("gcs_total"):
        parts.append(f"GCS: {vitals['gcs_total']}")
    if vitals.get("oxygen_delivery"):
        o2 = vitals["oxygen_delivery"]
        if vitals.get("oxygen_flow_rate"):
            o2 += f" at {vitals['oxygen_flow_rate']}"
        parts.append(f"O2: {o2}")
    return "Vitals: " + " | ".join(parts) if parts else "Vitals: Not available"


def _format_conditions(conditions: list) -> str:
    if not conditions:
        return "Active Conditions: None documented"
    items = []
    for c in conditions:
        display = c.get("display", "Unknown")
        severity = c.get("severity", "")
        items.append(f"- {display}" + (f" ({severity})" if severity else ""))
    return "Active Conditions:\n" + "\n".join(items)


def _format_medications(meds: list) -> str:
    if not meds:
        return "Current Medications: None documented"
    items = []
    for m in meds:
        parts = [m.get("name", "Unknown")]
        if m.get("dose"):
            parts.append(f"{m['dose']} {m.get('dose_unit', '')}")
        if m.get("route"):
            parts.append(m["route"])
        if m.get("frequency"):
            parts.append(m["frequency"])
        items.append("- " + " ".join(parts))
    return "Current Medications:\n" + "\n".join(items)


def _format_labs(labs: list) -> str:
    if not labs:
        return "Lab Results: None available"
    items = []
    for lab in labs:
        line = f"- {lab.get('name', 'Unknown')}: {lab.get('value', 'N/A')}"
        if lab.get("unit"):
            line += f" {lab['unit']}"
        if lab.get("flag"):
            line += f" [{lab['flag']}]"
        if lab.get("reference_range_text"):
            line += f" (ref: {lab['reference_range_text']})"
        items.append(line)
    return "Lab Results:\n" + "\n".join(items)


def _format_imaging(imaging: list) -> str:
    if not imaging:
        return "Imaging: None available"
    items = []
    for img in imaging:
        line = f"- {img.get('type', 'Unknown')}: {img.get('finding', 'No finding reported')}"
        if img.get("impression"):
            line += f" — Impression: {img['impression']}"
        items.append(line)
    return "Imaging:\n" + "\n".join(items)


def _format_allergies(allergies: list) -> str:
    if not allergies:
        return "Allergies: NKDA (No Known Drug Allergies)"
    return "Allergies: " + ", ".join(str(a) for a in allergies)


def _format_clinical_data(patient: Patient) -> str:
    sections = [
        _format_vitals(patient.vitals or {}),
        _format_conditions(patient.active_conditions or []),
        _format_medications(patient.current_medications or []),
        _format_labs(patient.lab_results or []),
        _format_imaging(patient.imaging_results or []),
        _format_allergies(patient.allergies or []),
        f"Code Status: {patient.code_status or 'FULL_CODE'}",
    ]
    if patient.medical_history:
        history_items = [f"- {h}" if isinstance(h, str) else f"- {h.get('display', str(h))}" for h in patient.medical_history]
        sections.append("Medical History:\n" + "\n".join(history_items))
    return "\n\n".join(sections)


def generate_sbar_template(
    patient: Patient,
    reason: str,
    urgency: str,
    specialty: str | None = None,
    additional_context: str | None = None,
) -> dict[str, str]:
    """Template-based SBAR generation (no LLM required)."""
    age = patient.age
    gender_full = {"M": "male", "F": "female"}.get(patient.gender or "", patient.gender or "")

    vitals_text = _format_vitals(patient.vitals or {})
    conditions = patient.active_conditions or []
    primary_dx = conditions[0].get("display", "Unknown condition") if conditions else "Condition not specified"

    situation = (
        f"Transfer request for {patient.full_name}, a {age}-year-old {gender_full} "
        f"(DOB: {patient.date_of_birth}, MRN: {patient.mrn or 'N/A'}), "
        f"presenting with {primary_dx}. "
        f"Reason for transfer: {reason}. Urgency: {urgency}."
    )

    # Background
    bg_parts = []
    if patient.medical_history:
        history_items = [h if isinstance(h, str) else h.get("display", str(h)) for h in patient.medical_history]
        bg_parts.append("Past Medical History: " + ", ".join(history_items))
    bg_parts.append(_format_medications(patient.current_medications or []))
    bg_parts.append(_format_allergies(patient.allergies or []))
    bg_parts.append(f"Code Status: {patient.code_status or 'FULL_CODE'}")
    background = "\n".join(bg_parts)

    # Assessment
    assess_parts = [vitals_text]
    assess_parts.append(_format_labs(patient.lab_results or []))
    assess_parts.append(_format_imaging(patient.imaging_results or []))
    if additional_context:
        assess_parts.append(f"Additional Context: {additional_context}")
    assessment = "\n".join(assess_parts)

    recommendation = (
        f"Requesting {'EMERGENT' if urgency == 'EMERGENT' else urgency} transfer "
        f"to facility with {specialty or 'appropriate'} capability. "
        f"Patient requires {specialty or 'higher level of care'} not available at current facility."
    )

    return {
        "situation": situation,
        "background": background,
        "assessment": assessment,
        "recommendation": recommendation,
    }


def _get_llm_client(use_tool_model: bool = False):
    """Return (client, model) tuple based on configured provider priority:
    1. Azure OpenAI  2. OpenRouter  3. OpenAI direct  4. None

    If *use_tool_model* is True and the provider is OpenRouter, the
    tool-capable model (nvidia/nemotron-3-ultra) is returned instead of
    the default chat model so that function-calling / tools work.
    """
    from openai import AsyncOpenAI

    # 1. Azure OpenAI
    if settings.azure_openai_api_key and settings.azure_openai_endpoint:
        from openai import AsyncAzureOpenAI
        client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key,
            azure_endpoint=settings.azure_openai_endpoint,
            api_version=settings.azure_openai_api_version,
        )
        return client, settings.azure_openai_deployment_name

    # 2. OpenRouter (uses OpenAI-compatible API)
    if settings.openrouter_api_key:
        client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "http://localhost:4000",
                "X-Title": "IPTC - Patient Transfer Coordinator",
            },
        )
        model = settings.openrouter_tool_model if use_tool_model else settings.openrouter_model
        return client, model

    # 3. OpenAI direct
    if settings.openai_api_key:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        return client, "gpt-4"

    return None, None


async def generate_sbar_with_llm(
    patient: Patient,
    reason: str,
    urgency: str,
    specialty: str | None = None,
    additional_context: str | None = None,
) -> dict[str, str] | None:
    """Generate SBAR using LLM. Returns None if no provider is configured."""
    client, model = _get_llm_client()
    if not client:
        return None

    try:
        clinical_data = _format_clinical_data(patient)
        user_prompt = SBAR_USER_PROMPT.format(
            patient_name=patient.full_name,
            age=patient.age,
            gender_char=patient.gender or "",
            dob=patient.date_of_birth,
            mrn=patient.mrn or "N/A",
            reason=reason,
            urgency=urgency,
            specialty=specialty or "Not specified",
            clinical_data=clinical_data,
            additional_context=additional_context or "None",
        )

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SBAR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=2000,
            ),
            timeout=settings.llm_timeout_sbar,
        )

        content = response.choices[0].message.content
        parsed = extract_json(content)
        return parsed if isinstance(parsed, dict) else None
    except asyncio.TimeoutError:
        print(f"LLM SBAR generation timed out after {settings.llm_timeout_sbar}s — falling back to template")
        return None
    except Exception as e:
        print(f"LLM SBAR generation failed: {e}")
        return None


async def generate_sbar(
    patient: Patient,
    reason: str,
    urgency: str,
    specialty: str | None = None,
    additional_context: str | None = None,
) -> tuple[dict[str, str], bool]:
    """Generate SBAR — tries LLM first, falls back to template.
    Returns (sbar_dict, was_ai_generated)."""
    llm_result = await generate_sbar_with_llm(patient, reason, urgency, specialty, additional_context)
    if llm_result and all(k in llm_result for k in ("situation", "background", "assessment", "recommendation")):
        return llm_result, True

    template_result = generate_sbar_template(patient, reason, urgency, specialty, additional_context)
    return template_result, False
