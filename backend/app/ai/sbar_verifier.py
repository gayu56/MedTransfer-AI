"""
SBAR Hallucination Guard — verifies AI-generated SBAR against source EHR data.
Flags any clinical values that don't trace back to source patient fields.
"""
import re
from app.models.patient import Patient


def verify_sbar_against_ehr(
    sbar: dict,
    patient: Patient,
    reason: str = "",
    urgency: str = "",
) -> dict:
    """
    Compare SBAR text against source EHR fields.
    Returns verification report with flagged values.
    """
    # Build set of known source values
    source_values = _extract_source_values(patient, reason, urgency)

    # Check each SBAR section
    sections = {
        "situation": sbar.get("situation", ""),
        "background": sbar.get("background", ""),
        "assessment": sbar.get("assessment", ""),
        "recommendation": sbar.get("recommendation", ""),
    }

    flags = []
    verified_count = 0
    total_clinical_values = 0

    for section_name, text in sections.items():
        extracted = _extract_clinical_values(text)
        for value_info in extracted:
            total_clinical_values += 1
            matched = _match_to_source(value_info, source_values)
            if matched:
                verified_count += 1
            else:
                flags.append({
                    "section": section_name,
                    "value": value_info["raw"],
                    "type": value_info["type"],
                    "message": f"Value '{value_info['raw']}' not found in source EHR data",
                })

    verification_score = (verified_count / total_clinical_values * 100) if total_clinical_values > 0 else 100.0

    return {
        "verified": len(flags) == 0,
        "verification_score": round(verification_score, 1),
        "total_values_checked": total_clinical_values,
        "verified_count": verified_count,
        "flags": flags,
        "source_data_available": bool(patient.vitals or patient.active_conditions or patient.lab_results),
    }


def _extract_source_values(patient: Patient, reason: str, urgency: str) -> set:
    """Build a set of all known source values from patient record."""
    values = set()

    # Patient demographics
    values.add(patient.full_name.lower())
    values.add(patient.first_name.lower())
    values.add(patient.last_name.lower())
    values.add(str(patient.age))
    values.add(patient.gender.lower())
    values.add(patient.mrn.lower())
    if patient.insurance_provider:
        values.add(patient.insurance_provider.lower())
    if patient.code_status:
        values.add(patient.code_status.lower())

    # Vitals
    vitals = patient.vitals or {}
    for key, val in vitals.items():
        if val is not None:
            values.add(str(val).lower())

    # Conditions
    for c in (patient.active_conditions or []):
        values.add(c.get("display", "").lower())
        if c.get("severity"):
            values.add(c["severity"].lower())
        if c.get("code"):
            values.add(str(c["code"]).lower())

    # Medications
    for m in (patient.current_medications or []):
        values.add(m.get("name", "").lower())
        if m.get("dose"):
            values.add(str(m["dose"]).lower())
        if m.get("frequency"):
            values.add(m["frequency"].lower())

    # Lab results
    for lab in (patient.lab_results or []):
        values.add(lab.get("name", "").lower())
        if lab.get("value") is not None:
            values.add(str(lab["value"]).lower())
        if lab.get("flag"):
            values.add(lab["flag"].lower())

    # Imaging
    for img in (patient.imaging_results or []):
        values.add(img.get("type", "").lower())
        if img.get("finding"):
            values.add(img["finding"].lower())

    # Allergies
    for a in (patient.allergies or []):
        values.add(str(a).lower())

    # Medical history
    for h in (patient.medical_history or []):
        if isinstance(h, str):
            values.add(h.lower())
        elif isinstance(h, dict):
            values.add(h.get("display", "").lower())

    # Transfer reason and urgency
    values.add(reason.lower())
    values.add(urgency.lower())

    # Remove empty strings
    values.discard("")
    return values


def _extract_clinical_values(text: str) -> list[dict]:
    """Extract clinical values (numbers, vital signs, lab results, medications) from text."""
    extracted = []

    # Blood pressure pattern: 120/80
    for m in re.finditer(r'\b(\d{2,3}/\d{2,3})\b', text):
        extracted.append({"raw": m.group(1), "type": "vital_bp", "components": m.group(1).split("/")})

    # Heart rate, RR, SpO2, temp patterns: "HR: 92", "SpO2: 99%"
    for m in re.finditer(r'(?:HR|heart rate|pulse)[:\s]+(\d+)', text, re.IGNORECASE):
        extracted.append({"raw": m.group(1), "type": "vital_hr"})

    for m in re.finditer(r'(?:RR|respiratory rate)[:\s]+(\d+)', text, re.IGNORECASE):
        extracted.append({"raw": m.group(1), "type": "vital_rr"})

    for m in re.finditer(r'(?:SpO2|O2 sat|oxygen sat)[:\s]+(\d+)', text, re.IGNORECASE):
        extracted.append({"raw": m.group(1), "type": "vital_spo2"})

    for m in re.finditer(r'(?:Temp|temperature)[:\s]+([\d.]+)', text, re.IGNORECASE):
        extracted.append({"raw": m.group(1), "type": "vital_temp"})

    for m in re.finditer(r'(?:GCS)[:\s]+(\d+)', text, re.IGNORECASE):
        extracted.append({"raw": m.group(1), "type": "vital_gcs"})

    for m in re.finditer(r'(?:Pain)[:\s]+(\d+)/10', text, re.IGNORECASE):
        extracted.append({"raw": m.group(1), "type": "vital_pain"})

    # Lab value pattern: "value unit" e.g. "2.1 mIU/L", "0 mg/dL"
    for m in re.finditer(r'([\d.]+)\s*(mg/dL|mIU/L|mmol/L|g/dL|%|mEq/L|U/L|ng/mL|mcg/mL)', text, re.IGNORECASE):
        extracted.append({"raw": m.group(1), "type": "lab_value"})

    return extracted


def _match_to_source(value_info: dict, source_values: set) -> bool:
    """Check if an extracted clinical value exists in the source data."""
    raw = value_info["raw"].lower()

    # Direct match
    if raw in source_values:
        return True

    # For BP, check both components
    if value_info["type"] == "vital_bp":
        components = value_info.get("components", [])
        return all(c in source_values for c in components)

    # Fuzzy: check if any source value contains this value
    for sv in source_values:
        if raw in sv or sv in raw:
            return True

    return False
