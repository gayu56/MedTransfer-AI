from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.call_log import CallLog
from app.models.transfer import TransferRequest, TransferTimeline, FacilityMatch
from app.models.facility import Facility, FacilityCapability, BedAvailability
from app.models.patient import Patient
from app.models.compliance import ComplianceRecord


async def create_call_log(
    db: AsyncSession,
    transfer_id: str,
    facility_id: str,
    called_by_user_id: str | None = None,
    contact_name: str | None = None,
    contact_role: str | None = None,
    phone_number: str | None = None,
    notes: str | None = None,
) -> CallLog:
    call = CallLog(
        transfer_id=transfer_id,
        facility_id=facility_id,
        called_by_user_id=called_by_user_id,
        contact_name=contact_name,
        contact_role=contact_role,
        phone_number=phone_number,
        notes=notes,
        call_started_at=datetime.now(timezone.utc),
        outcome="PENDING",
    )
    db.add(call)
    await db.flush()

    # Add timeline event
    facility = await db.get(Facility, facility_id)
    fname = facility.name if facility else "Unknown"
    timeline = TransferTimeline(
        transfer_id=transfer_id,
        event_type="CALL_INITIATED",
        event_description=f"Phone call initiated to {fname}" + (f" — {contact_name}" if contact_name else ""),
        triggered_by_user_id=called_by_user_id,
    )
    db.add(timeline)
    await db.flush()
    return call


async def update_call_log(
    db: AsyncSession,
    call_id: str,
    outcome: str,
    duration_seconds: int | None = None,
    notes: str | None = None,
    decline_reason: str | None = None,
    callback_time: str | None = None,
    contact_name: str | None = None,
    contact_role: str | None = None,
) -> CallLog | None:
    call = await db.get(CallLog, call_id)
    if not call:
        return None

    call.outcome = outcome
    call.call_ended_at = datetime.now(timezone.utc)
    call.updated_at = datetime.now(timezone.utc)

    if duration_seconds is not None:
        call.duration_seconds = duration_seconds
    if notes is not None:
        call.notes = notes
    if decline_reason is not None:
        call.decline_reason = decline_reason
    if callback_time is not None:
        call.callback_time = callback_time
    if contact_name is not None:
        call.contact_name = contact_name
    if contact_role is not None:
        call.contact_role = contact_role

    # Add timeline event
    facility = await db.get(Facility, call.facility_id)
    fname = facility.name if facility else "Unknown"
    outcome_text = outcome.replace("_", " ").title()

    timeline = TransferTimeline(
        transfer_id=call.transfer_id,
        event_type=f"CALL_{outcome}",
        event_description=f"Call to {fname} — {outcome_text}" + (f" — {decline_reason}" if decline_reason else "") + (f" — {notes}" if notes and not decline_reason else ""),
        triggered_by_user_id=call.called_by_user_id,
    )
    db.add(timeline)

    # If facility accepted via phone, update the transfer
    if outcome == "ACCEPTED":
        transfer = await db.get(TransferRequest, call.transfer_id)
        if transfer:
            transfer.receiving_facility_id = call.facility_id
            transfer.status = "ACCEPTED"
            transfer.accepted_at = datetime.now(timezone.utc)
            transfer.updated_at = datetime.now(timezone.utc)

            # Update facility match status
            matches_result = await db.execute(
                select(FacilityMatch).where(
                    FacilityMatch.transfer_id == call.transfer_id,
                    FacilityMatch.facility_id == call.facility_id,
                )
            )
            match = matches_result.scalar_one_or_none()
            if match:
                match.status = "ACCEPTED"
                match.responded_at = datetime.now(timezone.utc)

            # Update compliance — explicit query to avoid lazy-load in async
            cr_result = await db.execute(
                select(ComplianceRecord).where(ComplianceRecord.transfer_id == call.transfer_id)
            )
            cr = cr_result.scalar_one_or_none()
            if cr:
                cr.receiving_facility_confirmed = True
                cr.receiving_confirmed_at = datetime.now(timezone.utc)

    elif outcome == "DECLINED":
        # Update facility match
        matches_result = await db.execute(
            select(FacilityMatch).where(
                FacilityMatch.transfer_id == call.transfer_id,
                FacilityMatch.facility_id == call.facility_id,
            )
        )
        match = matches_result.scalar_one_or_none()
        if match:
            match.status = "DECLINED"
            match.declined_reason = decline_reason
            match.responded_at = datetime.now(timezone.utc)

    await db.flush()
    return call


async def simulate_call_outcome(
    db: AsyncSession,
    transfer_id: str,
    facility_id: str,
) -> dict:
    """
    Use LLM to simulate a realistic call outcome based on facility capabilities
    and patient needs. Returns outcome + simulated conversation details.
    """
    from app.ai.sbar_generator import _get_llm_client
    import json as _json

    # Load transfer + patient + facility data
    result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.id == transfer_id)
        .options(
            selectinload(TransferRequest.patient),
            selectinload(TransferRequest.sending_facility),
            selectinload(TransferRequest.clinical_summary),
        )
    )
    transfer = result.scalar_one_or_none()

    # Eagerly load facility with capabilities and bed availability
    fac_result = await db.execute(
        select(Facility)
        .where(Facility.id == facility_id)
        .options(
            selectinload(Facility.capabilities),
            selectinload(Facility.bed_availability),
        )
    )
    facility = fac_result.scalar_one_or_none()

    if not transfer or not facility:
        return {"outcome": "NO_ANSWER", "contact_name": None, "contact_role": None, "notes": "Could not reach facility."}

    patient = transfer.patient

    # Check if facility has the needed capability
    cap_names = [c.name for c in facility.capabilities] if facility.capabilities else []
    specialty = (transfer.requested_specialty or "").upper()
    has_capability = any(specialty in str(c).upper() for c in cap_names) if specialty else True
    accepting = facility.accepts_transfers
    total_avail_beds = sum(b.available_beds for b in facility.bed_availability) if facility.bed_availability else None

    client, model = _get_llm_client()
    if not client:
        # Fallback: simple rule-based simulation
        if not accepting:
            return {"outcome": "DECLINED", "contact_name": "Charge Nurse", "contact_role": "RN", "notes": "Facility not currently accepting transfers.", "decline_reason": "Not accepting transfers at this time."}
        if not has_capability:
            return {"outcome": "DECLINED", "contact_name": "Transfer Center", "contact_role": "Coordinator", "notes": f"Facility does not have {specialty} capability.", "decline_reason": f"No {specialty} capability."}
        return {"outcome": "ACCEPTED", "contact_name": "Dr. Williams", "contact_role": "Attending Physician", "notes": f"Accepted patient {patient.full_name}. Bed available."}

    # AI-powered simulation
    prompt = f"""You are simulating a phone call between a sending hospital's transfer coordinator and a receiving facility.
Based on the data below, generate a REALISTIC call outcome.

RECEIVING FACILITY: {facility.name}
- Capabilities: {', '.join(cap_names) if cap_names else 'General'}
- Accepts transfers: {accepting}
- Beds available: {total_avail_beds if total_avail_beds is not None else 'Unknown'}
- Location: {facility.city}, {facility.state}

PATIENT: {patient.full_name}, {patient.age}{patient.gender}
- Urgency: {transfer.urgency}
- Reason: {transfer.reason_for_transfer}
- Specialty needed: {specialty or 'General'}
- Insurance: {patient.insurance_provider or 'Unknown'}

RULES:
- If the facility lacks the needed specialty/capability, they should DECLINE
- If facility is not accepting transfers, DECLINE
- If the top-ranked facility (#1 or #2) has capability, they usually ACCEPT
- ~30% chance of NO_ANSWER or VOICEMAIL for lower-ranked facilities
- Include a realistic contact person name and role

Return ONLY valid JSON:
{{
  "outcome": "ACCEPTED" | "DECLINED" | "NO_ANSWER" | "VOICEMAIL" | "CALLBACK_REQUESTED",
  "contact_name": "name or null",
  "contact_role": "role or null",
  "notes": "brief conversation summary",
  "decline_reason": "reason if declined, null otherwise",
  "duration_seconds": estimated_call_duration_in_seconds
}}"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You simulate hospital transfer phone calls. Return only JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        data = _json.loads(response.choices[0].message.content)
        # Validate outcome
        valid_outcomes = {"ACCEPTED", "DECLINED", "NO_ANSWER", "VOICEMAIL", "CALLBACK_REQUESTED"}
        if data.get("outcome") not in valid_outcomes:
            data["outcome"] = "NO_ANSWER"
        return data
    except Exception as e:
        print(f"LLM call simulation failed: {e}")
        # Fallback
        if has_capability and accepting:
            return {"outcome": "ACCEPTED", "contact_name": "Dr. Smith", "contact_role": "Attending", "notes": "Accepted after review."}
        return {"outcome": "DECLINED", "contact_name": "Transfer Center", "contact_role": "RN", "notes": "Unable to accept.", "decline_reason": "No capacity."}


async def run_auto_call_sequence(
    db: AsyncSession,
    transfer_id: str,
) -> list[dict]:
    """
    Simulate calling facilities in rank order. AI generates realistic outcomes.
    IMPORTANT: Does NOT auto-accept. If AI predicts acceptance, it marks the call
    as PENDING_CONFIRMATION — coordinator must confirm with accepting physician name.
    """
    # Get facility matches ordered by rank
    matches_result = await db.execute(
        select(FacilityMatch)
        .where(FacilityMatch.transfer_id == transfer_id)
        .order_by(FacilityMatch.rank)
    )
    matches = list(matches_result.scalars().all())

    # Filter to only uncalled/non-declined facilities
    callable_matches = [m for m in matches if m.status not in ("ACCEPTED", "DECLINED", "PENDING_CONFIRMATION")]

    results = []
    for match in callable_matches:
        facility = await db.get(Facility, match.facility_id)
        fname = facility.name if facility else "Unknown"

        # Create the call log (marked as simulated)
        call = CallLog(
            transfer_id=transfer_id,
            facility_id=match.facility_id,
            called_by_user_id="user-sarah-01",
            notes=f"AI-simulated call to {fname}",
            call_started_at=datetime.now(timezone.utc),
            outcome="PENDING",
            is_simulated=True,
            human_confirmed=False,
        )
        db.add(call)
        await db.flush()

        # Simulate the call outcome
        sim = await simulate_call_outcome(db, transfer_id, match.facility_id)
        sim_outcome = sim.get("outcome", "NO_ANSWER")

        # Update call with simulated outcome
        call.call_ended_at = datetime.now(timezone.utc)
        call.duration_seconds = sim.get("duration_seconds")
        call.notes = sim.get("notes")
        call.contact_name = sim.get("contact_name")
        call.contact_role = sim.get("contact_role")

        if sim_outcome == "ACCEPTED":
            # DO NOT auto-accept — mark as pending human confirmation
            call.outcome = "PENDING_CONFIRMATION"
            match.status = "PENDING_CONFIRMATION"
        elif sim_outcome == "DECLINED":
            call.outcome = "DECLINED"
            call.decline_reason = sim.get("decline_reason")
            match.status = "DECLINED"
            match.declined_reason = sim.get("decline_reason")
            match.responded_at = datetime.now(timezone.utc)
        else:
            call.outcome = sim_outcome  # NO_ANSWER, VOICEMAIL, etc.

        # Add timeline event
        timeline = TransferTimeline(
            transfer_id=transfer_id,
            event_type=f"AUTO_CALL_{call.outcome}",
            event_description=f"AI-simulated call to {fname} — {call.outcome.replace('_', ' ').title()}"
                + (f": {sim.get('notes', '')}" if sim.get('notes') else ""),
            triggered_by_user_id="user-sarah-01",
        )
        db.add(timeline)

        result_entry = {
            "call_id": call.id,
            "facility_id": match.facility_id,
            "facility_name": fname,
            "rank": match.rank,
            "outcome": call.outcome,
            "contact_name": sim.get("contact_name"),
            "contact_role": sim.get("contact_role"),
            "notes": sim.get("notes"),
            "decline_reason": sim.get("decline_reason"),
            "is_simulated": True,
            "needs_confirmation": call.outcome == "PENDING_CONFIRMATION",
        }
        results.append(result_entry)

        # If likely accepted, stop calling — but still needs confirmation
        if call.outcome == "PENDING_CONFIRMATION":
            break

    await db.commit()
    return results


async def confirm_acceptance(
    db: AsyncSession,
    call_id: str,
    accepting_physician: str,
    contact_name: str | None = None,
    contact_role: str | None = None,
    notes: str | None = None,
) -> CallLog | None:
    """
    Human-confirmed acceptance. Only this function actually updates
    the transfer to ACCEPTED status. Requires accepting physician name.
    """
    call = await db.get(CallLog, call_id)
    if not call:
        return None

    call.outcome = "ACCEPTED"
    call.accepting_physician = accepting_physician
    call.human_confirmed = True
    call.updated_at = datetime.now(timezone.utc)
    if contact_name:
        call.contact_name = contact_name
    if contact_role:
        call.contact_role = contact_role
    if notes:
        call.notes = (call.notes or "") + f" | Confirmed: {notes}"

    # NOW update the transfer status — human verified
    transfer = await db.get(TransferRequest, call.transfer_id)
    if transfer:
        transfer.receiving_facility_id = call.facility_id
        transfer.status = "ACCEPTED"
        transfer.accepted_at = datetime.now(timezone.utc)
        transfer.updated_at = datetime.now(timezone.utc)

    # Update facility match
    matches_result = await db.execute(
        select(FacilityMatch).where(
            FacilityMatch.transfer_id == call.transfer_id,
            FacilityMatch.facility_id == call.facility_id,
        )
    )
    match = matches_result.scalar_one_or_none()
    if match:
        match.status = "ACCEPTED"
        match.responded_at = datetime.now(timezone.utc)

    # Update compliance
    cr_result = await db.execute(
        select(ComplianceRecord).where(ComplianceRecord.transfer_id == call.transfer_id)
    )
    cr = cr_result.scalar_one_or_none()
    if cr:
        cr.receiving_facility_confirmed = True
        cr.receiving_confirmed_at = datetime.now(timezone.utc)

    # Timeline
    facility = await db.get(Facility, call.facility_id)
    fname = facility.name if facility else "Unknown"
    timeline = TransferTimeline(
        transfer_id=call.transfer_id,
        event_type="ACCEPTANCE_CONFIRMED",
        event_description=f"Transfer accepted by {fname} — Accepting physician: Dr. {accepting_physician} (human-confirmed)",
        triggered_by_user_id=call.called_by_user_id,
    )
    db.add(timeline)

    await db.commit()
    return call


async def get_calls_for_transfer(db: AsyncSession, transfer_id: str) -> list[CallLog]:
    result = await db.execute(
        select(CallLog)
        .where(CallLog.transfer_id == transfer_id)
        .options(selectinload(CallLog.facility))
        .order_by(CallLog.created_at.desc())
    )
    return list(result.scalars().all())


async def generate_call_script(
    db: AsyncSession,
    transfer_id: str,
    facility_id: str,
) -> dict:
    """Generate a phone call script from transfer + patient data."""
    # Load transfer with patient
    result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.id == transfer_id)
        .options(
            selectinload(TransferRequest.patient),
            selectinload(TransferRequest.sending_facility),
            selectinload(TransferRequest.clinical_summary),
        )
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        return {"script": "Transfer not found.", "key_points": [], "questions_to_ask": []}

    facility = await db.get(Facility, facility_id)
    if not facility:
        return {"script": "Facility not found.", "key_points": [], "questions_to_ask": []}

    patient = transfer.patient
    cs = transfer.clinical_summary

    # Try AI-generated script
    ai_script = await _generate_script_with_llm(transfer, patient, facility, cs)
    if ai_script:
        return ai_script

    # Fallback: template-based script
    return _generate_template_script(transfer, patient, facility, cs)


def _generate_template_script(transfer, patient, facility, cs) -> dict:
    """Generate a template-based call script."""
    p = patient
    vitals = p.vitals or {}
    conditions = p.active_conditions or []
    condition_list = ", ".join([c.get("display", "") for c in conditions[:3]]) if conditions else "See chart"

    bp = f"{vitals.get('bp_systolic', '?')}/{vitals.get('bp_diastolic', '?')}" if vitals else "N/A"
    hr = vitals.get("heart_rate", "N/A") if vitals else "N/A"
    spo2 = vitals.get("spo2", "N/A") if vitals else "N/A"

    sending_name = transfer.sending_facility.name if transfer.sending_facility else "our facility"

    # Use SBAR if available
    situation = cs.situation if cs else f"Requesting transfer for {p.full_name}, {p.age}{p.gender}, with {transfer.reason_for_transfer}"
    background = cs.background if cs else f"Active conditions: {condition_list}. Vitals: BP {bp}, HR {hr}, SpO2 {spo2}%."
    assessment = cs.assessment if cs else f"Patient requires {transfer.requested_specialty or 'specialized care'} not available at {sending_name}."
    recommendation = cs.recommendation if cs else f"Requesting {transfer.urgency.lower()} transfer to your facility."

    script = f"""Hello, this is the Transfer Center at {sending_name}.

I'm calling to request a patient transfer to {facility.name}.

PATIENT: {p.full_name}, {p.age}-year-old {p.gender}, MRN {p.mrn}
INSURANCE: {p.insurance_provider or 'Unknown'}
CODE STATUS: {p.code_status}
URGENCY: {transfer.urgency}

SITUATION:
{situation}

BACKGROUND:
{background}

ASSESSMENT:
{assessment}

RECOMMENDATION:
{recommendation}

Can you accept this patient? Do you have an available {transfer.requested_unit_type or 'bed'} in {transfer.requested_specialty or 'your unit'}?"""

    key_points = [
        f"Patient: {p.full_name}, {p.age}{p.gender}",
        f"Urgency: {transfer.urgency}",
        f"Reason: {transfer.reason_for_transfer[:100]}",
        f"Specialty needed: {transfer.requested_specialty or 'General'}",
        f"Insurance: {p.insurance_provider or 'Unknown'}",
        f"Code status: {p.code_status}",
    ]

    questions = [
        "Can you accept this patient?",
        f"Do you have a {transfer.requested_unit_type or 'bed'} available?",
        f"Is a {transfer.requested_specialty or 'specialist'} available to take this case?",
        "What is the accepting physician's name?",
        "Is there anything you need from us before transfer?",
        "What is the estimated time for bed readiness?",
    ]

    return {
        "script": script,
        "key_points": key_points,
        "questions_to_ask": questions,
        "facility_name": facility.name,
        "facility_phone": facility.phone,
    }


async def _generate_script_with_llm(transfer, patient, facility, cs) -> dict | None:
    """Generate call script using LLM. Returns None if no provider configured."""
    from app.ai.sbar_generator import _get_llm_client

    client, model = _get_llm_client()
    if not client:
        return None

    p = patient
    vitals = p.vitals or {}
    conditions = p.active_conditions or []
    meds = p.current_medications or []

    sbar_text = ""
    if cs:
        sbar_text = f"""
SBAR Summary (already generated):
- Situation: {cs.situation}
- Background: {cs.background}
- Assessment: {cs.assessment}
- Recommendation: {cs.recommendation}
"""

    system_prompt = """You are an expert hospital transfer coordinator. Generate a professional phone call script 
for calling a receiving facility to request a patient transfer. The script should be:
- Clear and concise for verbal delivery over the phone
- Follow SBAR format naturally in conversation
- Include all critical patient information
- Be professional but urgent when appropriate
- Include pauses for the receiving facility to respond

Return your response in this exact JSON format:
{
  "script": "The full call script with [PAUSE] markers where the caller should wait for response",
  "key_points": ["bullet point 1", "bullet point 2", ...],
  "questions_to_ask": ["question 1", "question 2", ...]
}"""

    user_prompt = f"""Generate a phone call script for this transfer:

CALLING: {facility.name} ({facility.phone or 'No phone on file'})
FROM: {transfer.sending_facility.name if transfer.sending_facility else 'Our Facility'}

PATIENT: {p.full_name}, {p.age}-year-old {p.gender}
MRN: {p.mrn}
INSURANCE: {p.insurance_provider or 'Unknown'} — {p.insurance_plan_name or ''}
CODE STATUS: {p.code_status}
ALLERGIES: {', '.join(p.allergies) if p.allergies else 'NKDA'}

URGENCY: {transfer.urgency}
REASON: {transfer.reason_for_transfer}
SPECIALTY NEEDED: {transfer.requested_specialty or 'Not specified'}
UNIT TYPE: {transfer.requested_unit_type or 'Not specified'}

VITALS: BP {vitals.get('bp_systolic', '?')}/{vitals.get('bp_diastolic', '?')}, HR {vitals.get('heart_rate', '?')}, RR {vitals.get('respiratory_rate', '?')}, SpO2 {vitals.get('spo2', '?')}%, Temp {vitals.get('temperature', '?')}°{vitals.get('temperature_unit', 'F')}
CONDITIONS: {', '.join([c.get('display', '') for c in conditions[:5]])}
MEDICATIONS: {', '.join([m.get('name', '') for m in meds[:5]])}
{sbar_text}
ADDITIONAL NOTES: {transfer.additional_notes or 'None'}"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        import json
        content = response.choices[0].message.content
        data = json.loads(content)
        data["facility_name"] = facility.name
        data["facility_phone"] = facility.phone
        return data
    except Exception as e:
        print(f"LLM call script generation failed: {e}")
        return None
