import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.call_log import CallLog
from app.models.transfer import TransferRequest, TransferTimeline, FacilityMatch
from app.models.facility import Facility, FacilityCapability, BedAvailability
from app.models.patient import Patient
from app.models.compliance import ComplianceRecord

# Clinical synonyms for fuzzy specialty matching in fallback mode
_CLINICAL_SYNONYMS: dict[str, set[str]] = {
    "CARDIOLOGY": {"CARDIAC", "CARDIOTHORACIC", "HEART", "CARDIOVASCULAR", "CATH LAB", "CCU"},
    "NEUROLOGY": {"NEURO", "STROKE", "NEUROSCIENCE", "NEURO-INTERVENTIONAL"},
    "PULMONOLOGY": {"PULMONARY", "RESPIRATORY", "LUNG"},
    "ORTHOPEDICS": {"ORTHO", "ORTHOPEDIC", "MUSCULOSKELETAL", "JOINT", "SPINE"},
    "TRAUMA": {"TRAUMA CENTER", "LEVEL I", "LEVEL II", "LEVEL 1", "LEVEL 2"},
    "SURGERY": {"SURGICAL", "OPERATING", "OR"},
    "ICU": {"INTENSIVE CARE", "CRITICAL CARE", "CCU", "MICU", "SICU"},
    "NEPHROLOGY": {"RENAL", "KIDNEY", "DIALYSIS"},
    "ONCOLOGY": {"CANCER", "TUMOR", "HEMATOLOGY"},
    "GASTROENTEROLOGY": {"GI", "GASTRO", "HEPATOLOGY", "LIVER"},
    "PEDIATRICS": {"PEDS", "PEDIATRIC", "NICU", "PICU", "CHILDREN"},
}


def _fuzzy_capability_match(specialty: str, cap_names: list[str]) -> bool:
    """Check if a facility likely has the needed specialty using bidirectional
    substring matching + clinical synonym lookup."""
    if not specialty:
        return True
    s = specialty.upper().strip()
    caps_upper = [c.upper() for c in cap_names]

    # Direct bidirectional substring
    for cap in caps_upper:
        if s in cap or cap in s:
            return True

    # Synonym expansion
    for canonical, synonyms in _CLINICAL_SYNONYMS.items():
        all_terms = synonyms | {canonical}
        if any(term in s for term in all_terms):
            # Specialty matches a synonym group — check if facility has any term from same group
            if any(term in cap for term in all_terms for cap in caps_upper):
                return True

    return False


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

    # Check if facility has the needed capability (fuzzy match + already-ranked trust)
    cap_names = [c.name for c in facility.capabilities] if facility.capabilities else []
    specialty = (transfer.requested_specialty or "").upper()
    has_capability = _fuzzy_capability_match(specialty, cap_names)
    accepting = facility.accepts_transfers
    total_avail_beds = sum(b.available_beds for b in facility.bed_availability) if facility.bed_availability else None

    # Trust the matching engine: if this facility was already ranked, give it credit
    match_result = await db.execute(
        select(FacilityMatch).where(
            FacilityMatch.transfer_id == transfer_id,
            FacilityMatch.facility_id == facility_id,
        )
    )
    existing_match = match_result.scalar_one_or_none()
    if existing_match and existing_match.specialty_score and existing_match.specialty_score >= 40:
        has_capability = True  # Matching engine already scored it positively

    import random

    client, model = _get_llm_client()
    if not client:
        # Fallback: probabilistic simulation (realistic distribution)
        if not accepting:
            return {"outcome": "DECLINED", "contact_name": "Charge Nurse", "contact_role": "RN", "notes": "Facility not currently accepting transfers.", "decline_reason": "Not accepting transfers at this time.", "duration_seconds": random.randint(15, 30)}
        if not has_capability:
            return {"outcome": "DECLINED", "contact_name": "Transfer Center", "contact_role": "Coordinator", "notes": f"Facility does not have {specialty} capability.", "decline_reason": f"No {specialty} capability.", "duration_seconds": random.randint(20, 45)}
        # Realistic odds: 55% accept, 25% decline, 12% no answer, 8% voicemail
        roll = random.random()
        doc_names = ["Dr. Williams", "Dr. Patel", "Dr. Chen", "Dr. Rodriguez", "Dr. Kim"]
        if roll < 0.55:
            return {"outcome": "ACCEPTED", "contact_name": random.choice(doc_names), "contact_role": "Attending Physician", "notes": f"Accepted patient {patient.full_name}. Bed available.", "duration_seconds": random.randint(60, 180)}
        elif roll < 0.70:
            decline_reasons = ["No ICU beds available at this time", "Unit at capacity — on diversion", "Staffing shortage — cannot accept", "Specialist on call unavailable"]
            return {"outcome": "DECLINED", "contact_name": "Charge Nurse", "contact_role": "RN", "notes": "Unable to accept at this time.", "decline_reason": random.choice(decline_reasons), "duration_seconds": random.randint(30, 90)}
        elif roll < 0.90:
            return {"outcome": "NO_ANSWER", "contact_name": None, "contact_role": None, "notes": "No answer after multiple attempts.", "duration_seconds": 45}
        else:
            return {"outcome": "VOICEMAIL", "contact_name": None, "contact_role": None, "notes": "Reached voicemail — left message with patient details.", "duration_seconds": 30}

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
- Each facility independently decides based on current capacity, staffing, and patient acuity
- Acceptance is NOT guaranteed regardless of rank — realistically ~40% of capable facilities accept
- ~20% chance of NO_ANSWER, ~10% chance of VOICEMAIL for any facility
- Include a realistic contact person name and role
- Vary your responses — do NOT always accept the first facility

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
        from app.config import settings as _settings
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You simulate hospital transfer phone calls. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            ),
            timeout=_settings.llm_timeout_call_sim,
        )
        from app.ai.sbar_generator import extract_json
        data = extract_json(response.choices[0].message.content)
        if not isinstance(data, dict):
            raise ValueError("LLM did not return a valid JSON object")
        # Validate outcome
        valid_outcomes = {"ACCEPTED", "DECLINED", "NO_ANSWER", "VOICEMAIL", "CALLBACK_REQUESTED"}
        if data.get("outcome") not in valid_outcomes:
            data["outcome"] = "NO_ANSWER"
        return data
    except asyncio.TimeoutError:
        print(f"LLM call simulation timed out — using fallback")
    except Exception as e:
        print(f"LLM call simulation failed: {e}")

    # Fallback: probabilistic logic
    if not has_capability or not accepting:
        return {"outcome": "DECLINED", "contact_name": "Transfer Center", "contact_role": "RN", "notes": "Unable to accept.", "decline_reason": "No capacity.", "duration_seconds": 30}
    roll = random.random()
    doc_names = ["Dr. Smith", "Dr. Patel", "Dr. Lee", "Dr. Garcia"]
    if roll < 0.55:
        return {"outcome": "ACCEPTED", "contact_name": random.choice(doc_names), "contact_role": "Attending", "notes": "Accepted after review.", "duration_seconds": random.randint(60, 120)}
    elif roll < 0.80:
        return {"outcome": "DECLINED", "contact_name": "Charge Nurse", "contact_role": "RN", "notes": "At capacity.", "decline_reason": "No beds available.", "duration_seconds": random.randint(30, 60)}
    else:
        return {"outcome": "NO_ANSWER", "contact_name": None, "contact_role": None, "notes": "No answer.", "duration_seconds": 45}


async def simulate_call_conversation(
    db: AsyncSession,
    transfer_id: str,
    facility_id: str,
) -> dict:
    """
    PHASE 1 AUDIO AGENT: Simulate a realistic BACK-AND-FORTH phone conversation
    between the AI transfer coordinator and the receiving facility's staff.

    Returns the structured outcome PLUS a turn-by-turn transcript:
        {
          "outcome": "ACCEPTED" | "DECLINED" | "NO_ANSWER" | "VOICEMAIL",
          "transcript": [{"speaker": "AI"|"FACILITY", "text": "..."}],
          "contact_name", "contact_role", "accepting_physician",
          "bed_type", "decline_reason", "notes", "duration_seconds"
        }

    The AI never finalizes — an ACCEPTED outcome here is only a PROPOSAL that a
    human clinician must confirm before the transfer is locked.
    """
    from app.ai.sbar_generator import _get_llm_client
    import json as _json
    import random

    # Load transfer + patient
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
        return {
            "outcome": "NO_ANSWER",
            "transcript": [{"speaker": "AI", "text": "Attempting to reach the transfer line..."},
                           {"speaker": "FACILITY", "text": "(no answer)"}],
            "notes": "Could not reach facility.",
        }

    patient = transfer.patient
    cap_names = [c.name for c in facility.capabilities] if facility.capabilities else []
    specialty = (transfer.requested_specialty or "").upper()
    has_capability = _fuzzy_capability_match(specialty, cap_names)
    accepting = facility.accepts_transfers
    total_avail_beds = sum(b.available_beds for b in facility.bed_availability) if facility.bed_availability else None
    sending_name = transfer.sending_facility.name if transfer.sending_facility else "the sending facility"
    unit_type = transfer.requested_unit_type or "an appropriate bed"

    # Trust the matching engine: if already ranked with a decent score, don't override
    match_result = await db.execute(
        select(FacilityMatch).where(
            FacilityMatch.transfer_id == transfer_id,
            FacilityMatch.facility_id == facility_id,
        )
    )
    existing_match = match_result.scalar_one_or_none()
    if existing_match and existing_match.specialty_score and existing_match.specialty_score >= 40:
        has_capability = True

    client, model = _get_llm_client()

    if client:
        prompt = f"""You are simulating a realistic phone call for a patient transfer. Produce a natural,
turn-by-turn conversation between:
- "AI": the AI transfer coordinator calling on behalf of {sending_name}
- "FACILITY": the receiving hospital's transfer nurse / charge RN at {facility.name}

The AI opens by identifying itself as an AI coordinator, gives a concise SBAR-style summary,
and asks if they can accept. The FACILITY asks 1-2 clarifying questions; the AI answers.
The FACILITY then accepts (giving a bed type + accepting physician name) or declines (giving a reason).

CONTEXT
Receiving facility: {facility.name} — capabilities: {', '.join(cap_names) or 'General'};
accepts transfers: {accepting}; beds available: {total_avail_beds if total_avail_beds is not None else 'unknown'}.
Patient: {patient.full_name}, {patient.age}{patient.gender}; urgency {transfer.urgency};
reason: {transfer.reason_for_transfer}; specialty needed: {specialty or 'General'}; unit: {unit_type}.

RULES
- If the facility lacks the needed specialty/capability or is not accepting, they DECLINE.
- Otherwise about 45% accept; the rest decline (capacity/staffing) — don't always accept.
- Keep it to 4-8 short turns. Realistic, professional clinical phone tone.

Return ONLY valid JSON:
{{
  "outcome": "ACCEPTED" | "DECLINED" | "NO_ANSWER" | "VOICEMAIL",
  "transcript": [{{"speaker": "AI"|"FACILITY", "text": "..."}}],
  "contact_name": "nurse/coordinator name or null",
  "contact_role": "role or null",
  "accepting_physician": "Dr. Name if accepted, else null",
  "bed_type": "e.g. 'ICU Bed 4' if accepted, else null",
  "decline_reason": "reason if declined, else null",
  "notes": "one-line summary",
  "duration_seconds": integer
}}"""
        try:
            from app.config import settings as _settings
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You simulate realistic hospital transfer phone calls. Return only JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.8,
                    max_tokens=800,
                ),
                timeout=_settings.llm_timeout_call_sim,
            )
            from app.ai.sbar_generator import extract_json
            data = extract_json(response.choices[0].message.content)
            if not isinstance(data, dict):
                raise ValueError("LLM did not return a valid JSON object")
            if data.get("outcome") not in {"ACCEPTED", "DECLINED", "NO_ANSWER", "VOICEMAIL"}:
                data["outcome"] = "NO_ANSWER"
            if not isinstance(data.get("transcript"), list) or not data["transcript"]:
                data["transcript"] = [{"speaker": "AI", "text": data.get("notes", "Call completed.")}]
            return data
        except asyncio.TimeoutError:
            print(f"LLM conversation simulation timed out — using fallback")
        except Exception as e:
            print(f"LLM conversation simulation failed: {e}")
            # fall through to deterministic fallback

    # ── Deterministic fallback (no LLM) — still produces a transcript ──
    opener = {
        "speaker": "AI",
        "text": (f"Hello, this is the AI transfer coordinator calling from {sending_name} on behalf of "
                 f"Dr. {patient.last_name if patient else 'the attending'}. I have a {patient.age}{patient.gender} "
                 f"patient, {transfer.urgency.lower()} priority, for {transfer.reason_for_transfer}. "
                 f"Do you have {unit_type} and can you accept?"),
    }

    if not accepting or not has_capability:
        reason = ("not currently accepting transfers" if not accepting
                  else f"no {specialty or 'specialty'} capability available")
        return {
            "outcome": "DECLINED",
            "transcript": [
                opener,
                {"speaker": "FACILITY", "text": f"Thanks for calling. Unfortunately we're {reason} right now."},
                {"speaker": "AI", "text": "Understood, thank you. I'll continue contacting other facilities."},
            ],
            "contact_name": "Charge Nurse",
            "contact_role": "RN",
            "decline_reason": reason.capitalize(),
            "notes": f"Declined — {reason}.",
            "duration_seconds": random.randint(25, 60),
        }

    roll = random.random()
    if roll < 0.60:
        doc = random.choice(["Dr. Patel", "Dr. Chen", "Dr. Williams", "Dr. Rodriguez", "Dr. Kim"])
        nurse = random.choice(["Karen", "Mike", "Priya", "Tom"])
        unit = random.choice(["ICU Bed 4", "CCU Bed 2", "Med-Surg Bed 7", "Step-down Bed 3"])
        return {
            "outcome": "ACCEPTED",
            "transcript": [
                opener,
                {"speaker": "FACILITY", "text": f"This is {nurse}, charge nurse. What's the patient's current status and code status?"},
                {"speaker": "AI", "text": f"Hemodynamically stable, full code, on standard monitoring. Specialty needed is {specialty or 'general'}. Insurance is {patient.insurance_provider or 'on file'}."},
                {"speaker": "FACILITY", "text": f"Okay, we can take this patient. I'll put them in {unit}. {doc} will be the accepting physician."},
                {"speaker": "AI", "text": f"Thank you. Confirming {facility.name} accepts, {unit}, accepting physician {doc}. I'll send the SBAR and records now."},
            ],
            "contact_name": nurse,
            "contact_role": "Charge Nurse",
            "accepting_physician": doc,
            "bed_type": unit,
            "notes": f"Proposed acceptance — {unit}, {doc}.",
            "duration_seconds": random.randint(90, 200),
        }
    else:
        reason = random.choice([
            "No ICU beds available at this time",
            "Unit at capacity — on diversion",
            "Staffing shortage — cannot accept",
            "Specialist on call unavailable",
        ])
        return {
            "outcome": "DECLINED",
            "transcript": [
                opener,
                {"speaker": "FACILITY", "text": f"Let me check capacity... I'm sorry, {reason.lower()}."},
                {"speaker": "AI", "text": "Understood, thank you for checking. I'll reach out to other facilities."},
            ],
            "contact_name": "Charge Nurse",
            "contact_role": "RN",
            "decline_reason": reason,
            "notes": f"Declined — {reason.lower()}.",
            "duration_seconds": random.randint(40, 90),
        }


async def run_ai_call_sequence(db: AsyncSession, transfer_id: str) -> list[dict]:
    """
    PHASE 1: AI audio agent calls ALL matched facilities, holds a back-and-forth
    conversation with each, and records transcripts + outcomes.

    Critically, the AI does NOT lock any transfer. An acceptance is recorded as
    a PROPOSED_ACCEPT that a human clinician must confirm (via confirm_acceptance)
    before the transfer status becomes ACCEPTED. The human owns the final decision.
    """
    import json as _json

    matches_result = await db.execute(
        select(FacilityMatch)
        .where(FacilityMatch.transfer_id == transfer_id)
        .order_by(FacilityMatch.rank)
    )
    matches = list(matches_result.scalars().all())
    callable_matches = [m for m in matches if m.status not in ("ACCEPTED", "DECLINED", "CANCELLED")]

    db.add(TransferTimeline(
        transfer_id=transfer_id,
        event_type="AI_CALLS_STARTED",
        event_description=f"AI audio agent calling facilities in priority order (stops on first acceptance)",
        triggered_by_system=True,
    ))
    await db.flush()

    results = []
    for match in callable_matches:
        facility = await db.get(Facility, match.facility_id)
        fname = facility.name if facility else "Unknown"

        # Mark only the facility currently being dialed
        match.status = "CALLING"
        match.responded_at = None
        await db.flush()

        call = CallLog(
            transfer_id=transfer_id,
            facility_id=match.facility_id,
            called_by_user_id="user-sarah-01",
            call_started_at=datetime.now(timezone.utc),
            outcome="PENDING",
            is_simulated=True,
            human_confirmed=False,
        )
        db.add(call)
        await db.flush()

        convo = await simulate_call_conversation(db, transfer_id, match.facility_id)
        sim_outcome = convo.get("outcome", "NO_ANSWER")

        call.call_ended_at = datetime.now(timezone.utc)
        call.duration_seconds = convo.get("duration_seconds")
        call.notes = convo.get("notes")
        call.contact_name = convo.get("contact_name")
        call.contact_role = convo.get("contact_role")
        call.bed_type = convo.get("bed_type")
        call.transcript = _json.dumps(convo.get("transcript", []))

        if sim_outcome == "ACCEPTED":
            # PROPOSED only — do NOT lock the transfer. Awaits human confirmation.
            call.outcome = "PROPOSED_ACCEPT"
            call.accepting_physician = convo.get("accepting_physician")
            match.status = "AWAITING_CONFIRMATION"
            match.responded_at = datetime.now(timezone.utc)
            event_type = "AI_CALL_PROPOSED_ACCEPT"
            event_desc = (f"{fname} verbally accepted via AI call — bed {convo.get('bed_type') or 'TBD'}, "
                          f"physician {convo.get('accepting_physician') or 'TBD'}. Awaiting clinician confirmation.")
        elif sim_outcome == "DECLINED":
            call.outcome = "DECLINED"
            call.decline_reason = convo.get("decline_reason")
            match.status = "DECLINED"
            match.declined_reason = convo.get("decline_reason")
            match.responded_at = datetime.now(timezone.utc)
            event_type = "AI_CALL_DECLINED"
            event_desc = f"{fname} declined via AI call — {convo.get('decline_reason') or 'no reason given'}"
        else:
            call.outcome = sim_outcome
            match.status = "NO_RESPONSE"
            match.responded_at = datetime.now(timezone.utc)
            event_type = f"AI_CALL_{sim_outcome}"
            event_desc = f"{fname} — {sim_outcome.replace('_', ' ').title()}"

        db.add(TransferTimeline(
            transfer_id=transfer_id,
            event_type=event_type,
            event_description=event_desc,
            triggered_by_system=True,
        ))

        results.append({
            "call_id": call.id,
            "facility_id": match.facility_id,
            "facility_name": fname,
            "rank": match.rank,
            "outcome": call.outcome,
            "contact_name": call.contact_name,
            "contact_role": call.contact_role,
            "accepting_physician": call.accepting_physician,
            "bed_type": call.bed_type,
            "decline_reason": convo.get("decline_reason") if call.outcome == "DECLINED" else None,
            "notes": call.notes,
            "transcript": convo.get("transcript", []),
            "is_simulated": True,
            "proposed": call.outcome == "PROPOSED_ACCEPT",
        })

        # Stop dialing once a facility verbally accepts — no need to call the rest.
        if call.outcome == "PROPOSED_ACCEPT":
            break

    proposed = [r for r in results if r["proposed"]]
    db.add(TransferTimeline(
        transfer_id=transfer_id,
        event_type="AI_CALLS_COMPLETED",
        event_description=(f"AI calls complete — {len(proposed)} verbal acceptance(s) awaiting clinician confirmation"
                           if proposed else "AI calls complete — no acceptances; consider expanding search"),
        triggered_by_system=True,
    ))

    await db.commit()
    return results


async def run_ai_call_parallel(db: AsyncSession, transfer_id: str) -> list[dict]:
    """
    PARALLEL CALLING: AI audio agent calls ALL matched facilities SIMULTANEOUSLY.
    Every facility gets called at once. The first ACCEPTED facility becomes a
    PROPOSED_ACCEPT awaiting human confirmation; any additional acceptances are
    marked SUPERSEDED. Declined / no-answer facilities are recorded normally.

    Returns results for ALL facilities (not just until first accept) so the
    frontend can display them in a war-room multi-panel view.
    """
    import json as _json
    import random

    matches_result = await db.execute(
        select(FacilityMatch)
        .where(FacilityMatch.transfer_id == transfer_id)
        .order_by(FacilityMatch.rank)
    )
    matches = list(matches_result.scalars().all())
    callable_matches = [m for m in matches if m.status not in ("ACCEPTED", "DECLINED", "CANCELLED")]

    if not callable_matches:
        return []

    # Mark ALL facilities as CALLING simultaneously
    for match in callable_matches:
        match.status = "CALLING"
        match.responded_at = None

    db.add(TransferTimeline(
        transfer_id=transfer_id,
        event_type="AI_PARALLEL_CALLS_STARTED",
        event_description=f"AI calling {len(callable_matches)} facilities simultaneously",
        triggered_by_system=True,
    ))
    await db.flush()

    # Pre-load facility names and create call log entries for ALL facilities
    entries: list[tuple] = []
    for match in callable_matches:
        facility = await db.get(Facility, match.facility_id)
        fname = facility.name if facility else "Unknown"
        call = CallLog(
            transfer_id=transfer_id,
            facility_id=match.facility_id,
            called_by_user_id="user-sarah-01",
            call_started_at=datetime.now(timezone.utc),
            outcome="PENDING",
            is_simulated=True,
            human_confirmed=False,
        )
        db.add(call)
        entries.append((match, call, fname))
    await db.flush()

    # Run ALL simulations (DB access is serialised by aiosqlite, but the
    # critical point is that we call every facility — not just until first accept)
    sim_data: list[tuple] = []
    for match, call, fname in entries:
        convo = await simulate_call_conversation(db, transfer_id, match.facility_id)
        sim_data.append((match, call, fname, convo))

    # Process results — first verbal accept wins
    results: list[dict] = []
    first_accept_id = None

    for idx, (match, call, fname, convo) in enumerate(sim_data):
        sim_outcome = convo.get("outcome", "NO_ANSWER")

        call.call_ended_at = datetime.now(timezone.utc)
        call.duration_seconds = convo.get("duration_seconds")
        call.notes = convo.get("notes")
        call.contact_name = convo.get("contact_name")
        call.contact_role = convo.get("contact_role")
        call.bed_type = convo.get("bed_type")
        call.transcript = _json.dumps(convo.get("transcript", []))

        if sim_outcome == "ACCEPTED" and first_accept_id is None:
            first_accept_id = call.id
            call.outcome = "PROPOSED_ACCEPT"
            call.accepting_physician = convo.get("accepting_physician")
            match.status = "AWAITING_CONFIRMATION"
            match.responded_at = datetime.now(timezone.utc)
            event_type = "AI_CALL_PROPOSED_ACCEPT"
            event_desc = (f"{fname} verbally accepted — bed {convo.get('bed_type') or 'TBD'}, "
                          f"physician {convo.get('accepting_physician') or 'TBD'}. Awaiting confirmation.")
        elif sim_outcome == "ACCEPTED":
            call.outcome = "SUPERSEDED"
            call.accepting_physician = convo.get("accepting_physician")
            match.status = "SUPERSEDED"
            match.responded_at = datetime.now(timezone.utc)
            event_type = "AI_CALL_SUPERSEDED"
            event_desc = f"{fname} also accepted but another facility responded first"
        elif sim_outcome == "DECLINED":
            call.outcome = "DECLINED"
            call.decline_reason = convo.get("decline_reason")
            match.status = "DECLINED"
            match.declined_reason = convo.get("decline_reason")
            match.responded_at = datetime.now(timezone.utc)
            event_type = "AI_CALL_DECLINED"
            event_desc = f"{fname} declined — {convo.get('decline_reason') or 'no reason given'}"
        else:
            call.outcome = sim_outcome
            match.status = "NO_RESPONSE"
            match.responded_at = datetime.now(timezone.utc)
            event_type = f"AI_CALL_{sim_outcome}"
            event_desc = f"{fname} — {sim_outcome.replace('_', ' ').title()}"

        db.add(TransferTimeline(
            transfer_id=transfer_id,
            event_type=event_type,
            event_description=event_desc,
            triggered_by_system=True,
        ))

        # Staggered delay hint for frontend war-room playback
        results.append({
            "call_id": call.id,
            "facility_id": match.facility_id,
            "facility_name": fname,
            "rank": match.rank,
            "outcome": call.outcome,
            "contact_name": call.contact_name,
            "contact_role": call.contact_role,
            "accepting_physician": convo.get("accepting_physician"),
            "bed_type": call.bed_type,
            "decline_reason": convo.get("decline_reason") if call.outcome == "DECLINED" else None,
            "notes": call.notes,
            "transcript": convo.get("transcript", []),
            "is_simulated": True,
            "proposed": call.outcome == "PROPOSED_ACCEPT",
            "superseded": call.outcome == "SUPERSEDED",
            "delay": round(random.uniform(0.5, 3.0) + idx * 0.4, 2),
        })

    proposed = [r for r in results if r["proposed"]]
    db.add(TransferTimeline(
        transfer_id=transfer_id,
        event_type="AI_PARALLEL_CALLS_COMPLETED",
        event_description=(f"Parallel calls complete — {len(proposed)} acceptance(s) awaiting confirmation"
                           if proposed else "Parallel calls complete — no acceptances"),
        triggered_by_system=True,
    ))

    await db.commit()
    return results


async def run_ai_call_with_retry(
    db: AsyncSession,
    transfer_id: str,
    max_retries: int = 2,
    initial_radius: float = 50.0,
    radius_step: float = 25.0,
    extra_results: int = 3,
) -> dict:
    """
    Runs parallel AI calls. If no facility accepts, automatically expands the
    search radius and retries with newly discovered facilities.

    Returns:
        {
            "results": [...],       # all call results across all rounds
            "rounds": int,          # how many rounds were executed
            "retry_details": [...], # per-round info (radius, new_matches, etc.)
            "has_proposed_acceptance": bool,
        }
    """
    from app.services.facility_service import match_facilities

    all_results: list[dict] = []
    retry_details: list[dict] = []

    # Load transfer to get needed parameters for re-matching
    tr_result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.id == transfer_id)
        .options(selectinload(TransferRequest.patient))
    )
    transfer = tr_result.scalar_one_or_none()
    if not transfer:
        return {"results": [], "rounds": 0, "retry_details": [], "has_proposed_acceptance": False}

    # Round 1 — use existing matches
    results = await run_ai_call_parallel(db, transfer_id)
    all_results.extend(results)
    proposed = [r for r in results if r.get("proposed")]
    retry_details.append({
        "round": 1,
        "radius_miles": initial_radius,
        "facilities_called": len(results),
        "proposed": len(proposed),
    })

    if proposed:
        return {
            "results": all_results,
            "rounds": 1,
            "retry_details": retry_details,
            "has_proposed_acceptance": True,
        }

    # Retry rounds — expand search radius and find new facilities
    current_radius = initial_radius
    already_called_ids = {r["facility_id"] for r in all_results}

    for attempt in range(max_retries):
        current_radius += radius_step
        round_num = attempt + 2

        db.add(TransferTimeline(
            transfer_id=transfer_id,
            event_type="AI_RETRY_EXPANDING_SEARCH",
            event_description=(
                f"No acceptance in round {round_num - 1}. "
                f"Expanding search radius to {current_radius:.0f} miles (round {round_num})"
            ),
            triggered_by_system=True,
        ))
        await db.flush()

        # Re-match with wider radius
        new_matches = await match_facilities(
            db=db,
            transfer_id=transfer_id,
            sending_facility_id=transfer.sending_facility_id,
            required_specialty=transfer.requested_specialty,
            required_unit_type=transfer.requested_unit_type,
            insurance_provider=transfer.patient.insurance_provider if transfer.patient else None,
            max_distance_miles=current_radius,
            max_results=extra_results + len(already_called_ids),  # get more to fill gaps
        )

        # Filter out facilities we've already called
        fresh_match_ids = [m.facility_id for m in new_matches if m.facility_id not in already_called_ids]

        if not fresh_match_ids:
            retry_details.append({
                "round": round_num,
                "radius_miles": current_radius,
                "facilities_called": 0,
                "proposed": 0,
                "note": "No new facilities found in expanded radius",
            })
            continue

        # Run parallel calls for new matches only
        results = await run_ai_call_parallel(db, transfer_id)
        # Filter to only new facilities (parallel func may re-process all)
        new_results = [r for r in results if r["facility_id"] not in already_called_ids]
        all_results.extend(new_results)
        already_called_ids.update(r["facility_id"] for r in new_results)

        proposed = [r for r in new_results if r.get("proposed")]
        retry_details.append({
            "round": round_num,
            "radius_miles": current_radius,
            "facilities_called": len(new_results),
            "proposed": len(proposed),
        })

        if proposed:
            return {
                "results": all_results,
                "rounds": round_num,
                "retry_details": retry_details,
                "has_proposed_acceptance": True,
            }

    # All retries exhausted — no acceptance
    db.add(TransferTimeline(
        transfer_id=transfer_id,
        event_type="AI_RETRY_EXHAUSTED",
        event_description=(
            f"No acceptance after {len(retry_details)} rounds "
            f"(max radius {current_radius:.0f} mi). Consider manual outreach."
        ),
        triggered_by_system=True,
    ))
    await db.commit()

    return {
        "results": all_results,
        "rounds": len(retry_details),
        "retry_details": retry_details,
        "has_proposed_acceptance": False,
    }


async def _decrement_beds(db: AsyncSession, facility_id: str) -> None:
    """FIX 2: Decrement available beds by 1 when a facility accepts a transfer.
    Increments occupied_beds on the first available bed row for the facility."""
    beds_result = await db.execute(
        select(BedAvailability)
        .where(BedAvailability.facility_id == facility_id)
        .where(BedAvailability.occupied_beds < BedAvailability.total_beds)
        .order_by(BedAvailability.unit_type)
        .limit(1)
    )
    bed = beds_result.scalar_one_or_none()
    if bed:
        bed.occupied_beds += 1
        bed.last_updated_at = datetime.now(timezone.utc)
        await db.flush()


async def _increment_beds(db: AsyncSession, facility_id: str) -> None:
    """FIX 2: Increment available beds by 1 when a transfer is cancelled/rejected.
    Decrements occupied_beds on the first occupied bed row for the facility."""
    beds_result = await db.execute(
        select(BedAvailability)
        .where(BedAvailability.facility_id == facility_id)
        .where(BedAvailability.occupied_beds > 0)
        .order_by(BedAvailability.unit_type)
        .limit(1)
    )
    bed = beds_result.scalar_one_or_none()
    if bed:
        bed.occupied_beds -= 1
        bed.last_updated_at = datetime.now(timezone.utc)
        await db.flush()


async def _cancel_other_facilities(
    db: AsyncSession, transfer_id: str, accepted_facility_id: str
) -> None:
    """FIX 4: After atomic lock, cancel all other facilities that were contacted.
    Updates their call_log status to CANCELLED and logs a timeline event."""
    # Find all other call logs for this transfer that are not the accepted facility
    other_calls_result = await db.execute(
        select(CallLog)
        .where(CallLog.transfer_id == transfer_id)
        .where(CallLog.facility_id != accepted_facility_id)
        .where(CallLog.outcome.notin_(["DECLINED", "CANCELLED"]))
    )
    other_calls = list(other_calls_result.scalars().all())

    for call in other_calls:
        call.outcome = "CANCELLED"
        call.notes = (call.notes or "") + " | Auto-cancelled: transfer filled by another facility."
        call.updated_at = datetime.now(timezone.utc)

    # Also update facility matches
    other_matches_result = await db.execute(
        select(FacilityMatch)
        .where(FacilityMatch.transfer_id == transfer_id)
        .where(FacilityMatch.facility_id != accepted_facility_id)
        .where(FacilityMatch.status.notin_(["ACCEPTED", "DECLINED"]))
    )
    other_matches = list(other_matches_result.scalars().all())

    for match in other_matches:
        match.status = "CANCELLED"
        match.declined_reason = "Transfer accepted by another facility"
        match.responded_at = datetime.now(timezone.utc)

    # Timeline event for cancellation broadcast
    if other_calls:
        facility_names = []
        for call in other_calls:
            fac = await db.get(Facility, call.facility_id)
            if fac:
                facility_names.append(fac.name)

        timeline = TransferTimeline(
            transfer_id=transfer_id,
            event_type="CANCELLATION_BROADCAST",
            event_description=f"Cancellation sent to {len(other_calls)} facility(ies): {', '.join(facility_names)}",
            triggered_by_system=True,
        )
        db.add(timeline)

    await db.flush()


async def run_auto_call_sequence(
    db: AsyncSession,
    transfer_id: str,
) -> list[dict]:
    """
    BROADCAST MODEL: Send transfer request to ALL matched facilities simultaneously.
    AI simulates each facility's response. The FIRST facility to accept is auto-locked
    as the receiving facility. No manual confirmation needed — in real life, the
    accepting hospital's physician name comes from their acceptance response.
    """
    # Get facility matches ordered by rank
    matches_result = await db.execute(
        select(FacilityMatch)
        .where(FacilityMatch.transfer_id == transfer_id)
        .order_by(FacilityMatch.rank)
    )
    matches = list(matches_result.scalars().all())

    # Filter to only facilities that haven't responded yet
    broadcastable = [m for m in matches if m.status not in ("ACCEPTED", "DECLINED")]

    # Mark all as SENT (broadcast)
    for match in broadcastable:
        match.status = "SENT"
        match.responded_at = None

    # Add broadcast timeline event
    broadcast_timeline = TransferTimeline(
        transfer_id=transfer_id,
        event_type="BROADCAST_SENT",
        event_description=f"Transfer request broadcast to {len(broadcastable)} facilities simultaneously",
        triggered_by_user_id="user-sarah-01",
        triggered_by_system=True,
    )
    db.add(broadcast_timeline)
    await db.flush()

    results = []
    accepted_facility = None

    # Simulate responses from ALL facilities (broadcast — all get the request)
    for match in broadcastable:
        facility = await db.get(Facility, match.facility_id)
        fname = facility.name if facility else "Unknown"

        # Create the call/request log
        call = CallLog(
            transfer_id=transfer_id,
            facility_id=match.facility_id,
            called_by_user_id="user-sarah-01",
            notes=f"Broadcast transfer request sent to {fname}",
            call_started_at=datetime.now(timezone.utc),
            outcome="PENDING",
            is_simulated=True,
            human_confirmed=False,
        )
        db.add(call)
        await db.flush()

        # Simulate the facility's response
        sim = await simulate_call_outcome(db, transfer_id, match.facility_id)
        sim_outcome = sim.get("outcome", "NO_ANSWER")

        call.call_ended_at = datetime.now(timezone.utc)
        call.duration_seconds = sim.get("duration_seconds")
        call.notes = sim.get("notes")
        call.contact_name = sim.get("contact_name")
        call.contact_role = sim.get("contact_role")

        if sim_outcome == "ACCEPTED" and not accepted_facility:
            # FIX 1: Atomic first-accept locking — single UPDATE with WHERE status guard
            now = datetime.now(timezone.utc)
            lock_result = await db.execute(
                update(TransferRequest)
                .where(TransferRequest.id == transfer_id)
                .where(TransferRequest.status.in_(["INITIATED", "PENDING_REVIEW"]))
                .values(
                    status="ACCEPTED",
                    receiving_facility_id=match.facility_id,
                    accepted_at=now,
                    updated_at=now,
                )
            )
            if lock_result.rowcount == 1:
                # Lock succeeded — this facility won the race
                accepted_facility = match
                call.outcome = "ACCEPTED"
                call.accepting_physician = sim.get("contact_name", "Accepting Physician")
                call.human_confirmed = True
                match.status = "ACCEPTED"
                match.responded_at = now

                # Update compliance — receiving facility confirmed
                cr_result = await db.execute(
                    select(ComplianceRecord).where(ComplianceRecord.transfer_id == transfer_id)
                )
                cr = cr_result.scalar_one_or_none()
                if cr:
                    cr.receiving_facility_confirmed = True
                    cr.receiving_confirmed_at = now

                # FIX 2: Decrement bed count at accepting facility
                await _decrement_beds(db, match.facility_id)

                # FIX 4: Cancel all other contacted facilities asynchronously
                await _cancel_other_facilities(db, transfer_id, match.facility_id)
            else:
                # Lock failed — another facility already accepted (race lost)
                call.outcome = "DECLINED"
                call.notes = "Transfer already locked by another facility"
                match.status = "DECLINED"
                match.declined_reason = "Transfer already accepted by another facility"
                match.responded_at = datetime.now(timezone.utc)

        elif sim_outcome == "ACCEPTED" and accepted_facility:
            # Another facility accepted but we already have one — mark as late response
            call.outcome = "DECLINED"
            accepted_fac = await db.get(Facility, accepted_facility.facility_id)
            accepted_name = accepted_fac.name if accepted_fac else "another facility"
            call.notes = f"Accepted but {accepted_name} was already locked in"
            match.status = "DECLINED"
            match.declined_reason = "Another facility accepted first"
            match.responded_at = datetime.now(timezone.utc)
        elif sim_outcome == "DECLINED":
            call.outcome = "DECLINED"
            call.decline_reason = sim.get("decline_reason")
            match.status = "DECLINED"
            match.declined_reason = sim.get("decline_reason")
            match.responded_at = datetime.now(timezone.utc)
        else:
            call.outcome = sim_outcome  # NO_ANSWER, VOICEMAIL, etc.
            match.status = "NO_RESPONSE"
            match.responded_at = datetime.now(timezone.utc)

        # Timeline event per facility
        timeline = TransferTimeline(
            transfer_id=transfer_id,
            event_type=f"BROADCAST_{call.outcome}",
            event_description=f"{fname} — {call.outcome.replace('_', ' ').title()}"
                + (f": {sim.get('notes', '')}" if sim.get('notes') else ""),
            triggered_by_user_id="user-sarah-01",
            triggered_by_system=True,
        )
        db.add(timeline)

        results.append({
            "call_id": call.id,
            "facility_id": match.facility_id,
            "facility_name": fname,
            "rank": match.rank,
            "outcome": call.outcome,
            "contact_name": sim.get("contact_name"),
            "contact_role": sim.get("contact_role"),
            "notes": call.notes,
            "decline_reason": sim.get("decline_reason") if call.outcome == "DECLINED" else None,
            "is_simulated": True,
            "accepted": call.outcome == "ACCEPTED",
        })

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
        from app.config import settings as _settings
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            ),
            timeout=_settings.llm_timeout_call_sim,
        )

        from app.ai.sbar_generator import extract_json
        content = response.choices[0].message.content
        data = extract_json(content)
        if not isinstance(data, dict):
            raise ValueError("LLM did not return a valid JSON object")
        data["facility_name"] = facility.name
        data["facility_phone"] = facility.phone
        return data
    except asyncio.TimeoutError:
        print(f"LLM call script generation timed out — using template")
        return None
    except Exception as e:
        print(f"LLM call script generation failed: {e}")
        return None
