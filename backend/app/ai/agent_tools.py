"""
Agent tool definitions and executors.
Each tool is a function the LLM can call via OpenAI function calling.
"""
import json
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.patient import Patient
from app.models.transfer import TransferRequest, FacilityMatch, TransferTimeline
from app.models.facility import Facility
from app.models.compliance import ComplianceRecord
from app.models.call_log import CallLog

# ── Tool Definitions (OpenAI function calling format) ──────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_patient",
            "description": "Search for a patient by name or MRN. Use this when the user mentions a patient name or MRN.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Patient name or MRN to search for",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_details",
            "description": "Get full clinical details for a specific patient including vitals, conditions, medications, labs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "string",
                        "description": "The patient ID",
                    }
                },
                "required": ["patient_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_sbar",
            "description": "Generate an SBAR clinical summary for a patient transfer. Use this when the user wants to create a clinical summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "Patient ID"},
                    "reason": {"type": "string", "description": "Reason for transfer"},
                    "urgency": {"type": "string", "enum": ["EMERGENT", "URGENT", "ROUTINE"], "description": "Transfer urgency level"},
                    "specialty": {"type": "string", "description": "Required specialty (optional)"},
                },
                "required": ["patient_id", "reason", "urgency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_transfer",
            "description": "Create a new transfer request for a patient. Use after SBAR is generated and details are confirmed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "Patient ID"},
                    "urgency": {"type": "string", "enum": ["EMERGENT", "URGENT", "ROUTINE"]},
                    "reason_for_transfer": {"type": "string", "description": "Reason for transfer"},
                    "requested_specialty": {"type": "string", "description": "Required specialty"},
                    "requested_unit_type": {"type": "string", "description": "Required unit type (ICU, CCU, etc.)"},
                    "clinical_summary_id": {"type": "string", "description": "ID of the previously generated SBAR"},
                },
                "required": ["patient_id", "urgency", "reason_for_transfer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transfer_status",
            "description": "Get the current status and details of a transfer request including facility matches, compliance, and timeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string", "description": "Transfer ID"},
                },
                "required": ["transfer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_active_transfers",
            "description": "List all active (non-completed) transfers. Use when the user asks about ongoing transfers or dashboard status.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_emtala_compliance",
            "description": "Check the EMTALA compliance status for a transfer. Shows which items are complete and which are pending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string", "description": "Transfer ID"},
                },
                "required": ["transfer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_emtala_auto_checks",
            "description": "Run automatic EMTALA compliance checks for a transfer based on patient data and transfer state. Auto-verifies MSE, stabilization, receiving facility, and transport appropriateness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string", "description": "Transfer ID"},
                },
                "required": ["transfer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_facility_matches",
            "description": "Get the ranked facility matches for a transfer, showing which facilities can accept the patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string", "description": "Transfer ID"},
                },
                "required": ["transfer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_call_script",
            "description": "Generate a phone call script to call a receiving facility about a transfer. Use when the coordinator needs to call a facility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string", "description": "Transfer ID"},
                    "facility_id": {"type": "string", "description": "Facility ID to call"},
                },
                "required": ["transfer_id", "facility_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_next_action",
            "description": "Determine the next recommended action for a transfer based on its current state. Use when the user asks what to do next.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string", "description": "Transfer ID"},
                },
                "required": ["transfer_id"],
            },
        },
    },
]


# ── Tool Executors ─────────────────────────────────────────────────────────

async def execute_tool(tool_name: str, arguments: dict, db: AsyncSession) -> str:
    """Execute a tool and return the result as a string for the LLM."""
    executors = {
        "search_patient": _search_patient,
        "get_patient_details": _get_patient_details,
        "generate_sbar": _generate_sbar,
        "create_transfer": _create_transfer,
        "get_transfer_status": _get_transfer_status,
        "list_active_transfers": _list_active_transfers,
        "check_emtala_compliance": _check_emtala_compliance,
        "run_emtala_auto_checks": _run_emtala_auto_checks,
        "get_facility_matches": _get_facility_matches,
        "generate_call_script": _generate_call_script,
        "get_next_action": _get_next_action,
    }

    executor = executors.get(tool_name)
    if not executor:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    try:
        result = await executor(db, **arguments)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _search_patient(db: AsyncSession, query: str) -> dict:
    q = f"%{query}%"
    # Split query into parts to match first/last name individually
    parts = query.strip().split()
    conditions = [
        Patient.first_name.ilike(q),
        Patient.last_name.ilike(q),
        Patient.mrn.ilike(q),
    ]
    # If multi-word query like "Dorothy Anderson", also match each word separately
    for part in parts:
        p = f"%{part}%"
        conditions.append(Patient.first_name.ilike(p))
        conditions.append(Patient.last_name.ilike(p))

    result = await db.execute(
        select(Patient).where(or_(*conditions)).limit(5)
    )
    patients = result.scalars().all()

    # If multi-word, prioritize patients matching ALL parts
    if len(parts) > 1 and len(patients) > 1:
        def match_score(p):
            score = 0
            for part in parts:
                pl = part.lower()
                if pl in (p.first_name or "").lower() or pl in (p.last_name or "").lower():
                    score += 1
            return score
        patients = sorted(patients, key=match_score, reverse=True)

    if not patients:
        return {"found": False, "message": f"No patients found matching '{query}'"}

    return {
        "found": True,
        "count": len(patients),
        "patients": [
            {
                "id": p.id,
                "name": p.full_name,
                "mrn": p.mrn,
                "age": p.age,
                "gender": p.gender,
                "code_status": p.code_status,
                "conditions": [c.get("display", "") for c in (p.active_conditions or [])[:3]],
            }
            for p in patients
        ],
    }


async def _get_patient_details(db: AsyncSession, patient_id: str) -> dict:
    patient = await db.get(Patient, patient_id)
    if not patient:
        return {"error": "Patient not found"}

    vitals = patient.vitals or {}
    return {
        "id": patient.id,
        "name": patient.full_name,
        "mrn": patient.mrn,
        "dob": str(patient.date_of_birth),
        "age": patient.age,
        "gender": patient.gender,
        "code_status": patient.code_status,
        "insurance": patient.insurance_provider,
        "allergies": patient.allergies or [],
        "vitals": {
            "bp": f"{vitals.get('bp_systolic', '?')}/{vitals.get('bp_diastolic', '?')}",
            "hr": vitals.get("heart_rate", "?"),
            "rr": vitals.get("respiratory_rate", "?"),
            "spo2": vitals.get("spo2", "?"),
            "temp": vitals.get("temperature", "?"),
            "gcs": vitals.get("gcs_total", "?"),
        },
        "conditions": [c.get("display", "") for c in (patient.active_conditions or [])],
        "medications": [m.get("name", "") for m in (patient.current_medications or [])],
        "has_vitals": bool(vitals),
        "has_conditions": bool(patient.active_conditions),
        "has_medications": bool(patient.current_medications),
    }


async def _generate_sbar(db: AsyncSession, patient_id: str, reason: str, urgency: str, specialty: str | None = None) -> dict:
    from app.ai.sbar_generator import generate_sbar
    from app.models.clinical_summary import ClinicalSummary

    patient = await db.get(Patient, patient_id)
    if not patient:
        return {"error": "Patient not found"}

    sbar_dict, was_ai = await generate_sbar(
        patient=patient, reason=reason, urgency=urgency,
        specialty=specialty, additional_context=None,
    )

    summary = ClinicalSummary(
        transfer_id=None,
        patient_id=patient.id,
        situation=sbar_dict["situation"],
        background=sbar_dict["background"],
        assessment=sbar_dict["assessment"],
        recommendation=sbar_dict["recommendation"],
        vitals=patient.vitals,
        active_conditions=patient.active_conditions,
        current_medications=patient.current_medications,
        lab_results=patient.lab_results,
        imaging_results=patient.imaging_results,
        generated_by_ai=was_ai,
        ai_model_version="gpt-4" if was_ai else "template-v1",
    )
    db.add(summary)
    await db.flush()

    return {
        "sbar_id": summary.id,
        "generated_by_ai": was_ai,
        "situation": sbar_dict["situation"][:200],
        "background": sbar_dict["background"][:200],
        "assessment": sbar_dict["assessment"][:200],
        "recommendation": sbar_dict["recommendation"][:200],
    }


async def _create_transfer(
    db: AsyncSession, patient_id: str, urgency: str, reason_for_transfer: str,
    requested_specialty: str | None = None, requested_unit_type: str | None = None,
    clinical_summary_id: str | None = None,
) -> dict:
    from app.services import transfer_service, facility_service
    from app.models.clinical_summary import ClinicalSummary

    DEFAULT_FACILITY_ID = "facility-metro-general"
    DEFAULT_USER_ID = "user-sarah-01"

    transfer = await transfer_service.create_transfer(
        db=db, patient_id=patient_id, sending_facility_id=DEFAULT_FACILITY_ID,
        initiated_by_user_id=DEFAULT_USER_ID, urgency=urgency,
        reason_for_transfer=reason_for_transfer,
        requested_specialty=requested_specialty,
        requested_unit_type=requested_unit_type,
    )

    await facility_service.match_facilities(
        db=db, transfer_id=transfer.id,
        sending_facility_id=DEFAULT_FACILITY_ID,
        required_specialty=requested_specialty,
        required_unit_type=requested_unit_type,
    )
    transfer.status = "PENDING_REVIEW"

    if clinical_summary_id:
        result = await db.execute(
            select(ClinicalSummary).where(ClinicalSummary.id == clinical_summary_id)
        )
        summary = result.scalar_one_or_none()
        if summary:
            summary.transfer_id = transfer.id

    await db.flush()

    # Get facility matches count
    matches_result = await db.execute(
        select(FacilityMatch).where(FacilityMatch.transfer_id == transfer.id)
    )
    matches = matches_result.scalars().all()

    return {
        "transfer_id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "facilities_matched": len(matches),
        "top_facility": matches[0].facility_name if matches else "None",
    }


async def _get_transfer_status(db: AsyncSession, transfer_id: str) -> dict:
    result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.id == transfer_id)
        .options(
            selectinload(TransferRequest.patient),
            selectinload(TransferRequest.sending_facility),
            selectinload(TransferRequest.receiving_facility),
            selectinload(TransferRequest.compliance_record),
            selectinload(TransferRequest.facility_matches),
            selectinload(TransferRequest.timeline),
        )
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        return {"error": "Transfer not found"}

    cr = transfer.compliance_record
    return {
        "transfer_id": transfer.id,
        "transfer_number": transfer.transfer_number,
        "status": transfer.status,
        "urgency": transfer.urgency,
        "patient_name": transfer.patient.full_name if transfer.patient else "Unknown",
        "reason": transfer.reason_for_transfer,
        "sending_facility": transfer.sending_facility.name if transfer.sending_facility else None,
        "receiving_facility": transfer.receiving_facility.name if transfer.receiving_facility else None,
        "facility_matches_count": len(transfer.facility_matches or []),
        "emtala_complete": cr.all_checks_passed if cr else False,
        "emtala_summary": cr.checklist_summary if cr else None,
        "timeline_events": len(transfer.timeline or []),
        "initiated_at": str(transfer.initiated_at) if transfer.initiated_at else None,
        "accepted_at": str(transfer.accepted_at) if transfer.accepted_at else None,
    }


async def _list_active_transfers(db: AsyncSession) -> dict:
    result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.status.notin_(["COMPLETED", "CANCELLED"]))
        .options(selectinload(TransferRequest.patient))
        .order_by(TransferRequest.created_at.desc())
        .limit(10)
    )
    transfers = result.scalars().all()
    return {
        "count": len(transfers),
        "transfers": [
            {
                "id": t.id,
                "number": t.transfer_number,
                "patient": t.patient.full_name if t.patient else "Unknown",
                "status": t.status,
                "urgency": t.urgency,
                "reason": t.reason_for_transfer[:80],
            }
            for t in transfers
        ],
    }


async def _check_emtala_compliance(db: AsyncSession, transfer_id: str) -> dict:
    result = await db.execute(
        select(ComplianceRecord).where(ComplianceRecord.transfer_id == transfer_id)
    )
    cr = result.scalar_one_or_none()
    if not cr:
        return {"error": "No compliance record found for this transfer"}

    items = [
        {"name": "Medical Screening Exam", "field": "mse_completed", "done": cr.mse_completed, "auto": True},
        {"name": "Stabilization Documented", "field": "stabilization_attempted", "done": cr.stabilization_attempted, "auto": True},
        {"name": "MD Certification Signed", "field": "md_certification_signed", "done": cr.md_certification_signed, "auto": False},
        {"name": "Patient Consent", "field": "consent_obtained", "done": cr.consent_obtained, "auto": False},
        {"name": "Receiving Facility Confirmed", "field": "receiving_facility_confirmed", "done": cr.receiving_facility_confirmed, "auto": True},
        {"name": "Transport Appropriate", "field": "transport_appropriate", "done": cr.transport_appropriate, "auto": True},
        {"name": "Records Sent", "field": "records_sent", "done": cr.records_sent, "auto": False},
    ]

    done = [i for i in items if i["done"]]
    pending = [i for i in items if not i["done"]]

    return {
        "all_passed": cr.all_checks_passed,
        "completed": len(done),
        "total": len(items),
        "done_items": [i["name"] for i in done],
        "pending_items": [{"name": i["name"], "requires_manual": not i["auto"]} for i in pending],
        "can_dispatch": cr.all_checks_passed,
    }


async def _run_emtala_auto_checks(db: AsyncSession, transfer_id: str) -> dict:
    """Run automatic EMTALA checks based on patient data and transfer state."""
    result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.id == transfer_id)
        .options(
            selectinload(TransferRequest.patient),
            selectinload(TransferRequest.compliance_record),
            selectinload(TransferRequest.facility_matches),
        )
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        return {"error": "Transfer not found"}

    cr = transfer.compliance_record
    if not cr:
        return {"error": "No compliance record found"}

    patient = transfer.patient
    auto_checked = []
    already_done = []
    cannot_auto = []

    from datetime import datetime, timezone

    # 1. MSE — auto-check if patient has vitals
    if not cr.mse_completed:
        if patient and patient.vitals:
            cr.mse_completed = True
            cr.mse_completed_at = datetime.now(timezone.utc)
            auto_checked.append("Medical Screening Exam (patient has vitals on record)")
        else:
            cannot_auto.append("Medical Screening Exam (no vitals found — manual verification needed)")
    else:
        already_done.append("Medical Screening Exam")

    # 2. Stabilization — auto-check if patient has active conditions + medications
    if not cr.stabilization_attempted:
        if patient and patient.active_conditions and patient.current_medications:
            cr.stabilization_attempted = True
            cr.stabilization_notes = "Auto-verified: Patient has documented conditions and active treatment medications."
            auto_checked.append("Stabilization (patient has conditions + treatment documented)")
        else:
            cannot_auto.append("Stabilization (insufficient treatment documentation — manual verification needed)")
    else:
        already_done.append("Stabilization Documented")

    # 3. MD Certification — always manual
    if not cr.md_certification_signed:
        cannot_auto.append("MD Certification (requires physician signature — MANUAL)")
    else:
        already_done.append("MD Certification Signed")

    # 4. Patient Consent — always manual
    if not cr.consent_obtained:
        cannot_auto.append("Patient Consent (requires patient/family signature — MANUAL)")
    else:
        already_done.append("Patient Consent")

    # 5. Receiving Facility — auto-check if any facility match is ACCEPTED
    if not cr.receiving_facility_confirmed:
        accepted_matches = [m for m in (transfer.facility_matches or []) if m.status == "ACCEPTED"]
        if accepted_matches:
            cr.receiving_facility_confirmed = True
            cr.receiving_confirmed_at = datetime.now(timezone.utc)
            auto_checked.append(f"Receiving Facility Confirmed ({accepted_matches[0].facility_name})")
        else:
            cannot_auto.append("Receiving Facility (no facility has accepted yet — call facilities first)")
    else:
        already_done.append("Receiving Facility Confirmed")

    # 6. Transport Appropriate — auto-check based on urgency
    if not cr.transport_appropriate:
        transport_map = {
            "EMERGENT": "ALS Ambulance — critical patient requires advanced life support",
            "URGENT": "BLS Ambulance — stable but requires monitored transport",
            "ROUTINE": "BLS Ambulance or wheelchair van — stable patient",
        }
        level = transport_map.get(transfer.urgency, "BLS Ambulance")
        cr.transport_appropriate = True
        cr.transport_level_justified = f"Auto-determined: {level}"
        auto_checked.append(f"Transport Appropriate ({level})")
    else:
        already_done.append("Transport Appropriate")

    # 7. Records Sent — always manual
    if not cr.records_sent:
        cannot_auto.append("Records Sent (must confirm records are faxed/sent — MANUAL)")
    else:
        already_done.append("Records Sent")

    await db.flush()

    return {
        "auto_checked": auto_checked,
        "already_done": already_done,
        "requires_manual": cannot_auto,
        "all_passed": cr.all_checks_passed,
        "summary": f"{len(auto_checked)} items auto-verified, {len(already_done)} already done, {len(cannot_auto)} require manual action",
    }


async def _get_facility_matches(db: AsyncSession, transfer_id: str) -> dict:
    result = await db.execute(
        select(FacilityMatch)
        .where(FacilityMatch.transfer_id == transfer_id)
        .options(selectinload(FacilityMatch.facility))
        .order_by(FacilityMatch.rank)
    )
    matches = result.scalars().all()
    if not matches:
        return {"count": 0, "message": "No facility matches found for this transfer"}

    return {
        "count": len(matches),
        "matches": [
            {
                "rank": m.rank,
                "facility_id": m.facility_id,
                "facility_name": m.facility_name,
                "score": m.overall_score,
                "status": m.status,
                "distance_miles": m.distance_miles,
                "estimated_transport_min": m.estimated_transport_min,
                "phone": m.facility.phone if m.facility else None,
            }
            for m in matches
        ],
    }


async def _generate_call_script(db: AsyncSession, transfer_id: str, facility_id: str) -> dict:
    from app.services.call_service import generate_call_script
    return await generate_call_script(db, transfer_id, facility_id)


async def _get_next_action(db: AsyncSession, transfer_id: str) -> dict:
    """Determine the next recommended action for a transfer."""
    result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.id == transfer_id)
        .options(
            selectinload(TransferRequest.patient),
            selectinload(TransferRequest.compliance_record),
            selectinload(TransferRequest.facility_matches),
            selectinload(TransferRequest.clinical_summary),
        )
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        return {"error": "Transfer not found"}

    cr = transfer.compliance_record
    status = transfer.status
    actions = []

    if status == "INITIATED":
        actions.append({"action": "GENERATE_SBAR", "description": "Generate SBAR clinical summary", "priority": "HIGH"})

    elif status == "PENDING_REVIEW":
        # Check if any facility has been called
        calls_result = await db.execute(
            select(CallLog).where(CallLog.transfer_id == transfer_id)
        )
        calls = calls_result.scalars().all()
        accepted_calls = [c for c in calls if c.outcome == "ACCEPTED"]

        if not calls:
            uncalled = [m for m in (transfer.facility_matches or []) if m.status not in ("ACCEPTED", "DECLINED")]
            if uncalled:
                actions.append({
                    "action": "CALL_FACILITY",
                    "description": f"Call {uncalled[0].facility_name} (ranked #{uncalled[0].rank}, score {uncalled[0].overall_score})",
                    "facility_id": uncalled[0].facility_id,
                    "priority": "HIGH",
                })
        elif not accepted_calls:
            uncalled = [m for m in (transfer.facility_matches or []) if m.status not in ("ACCEPTED", "DECLINED")]
            if uncalled:
                actions.append({
                    "action": "CALL_NEXT_FACILITY",
                    "description": f"Previous calls declined. Call next: {uncalled[0].facility_name}",
                    "facility_id": uncalled[0].facility_id,
                    "priority": "HIGH",
                })
            else:
                actions.append({"action": "NO_FACILITIES", "description": "All facilities contacted and declined. Consider expanding search.", "priority": "CRITICAL"})

    elif status == "ACCEPTED":
        if cr and not cr.all_checks_passed:
            pending = []
            if not cr.md_certification_signed:
                pending.append("MD Certification (get physician to sign)")
            if not cr.consent_obtained:
                pending.append("Patient Consent (get patient/family to sign)")
            if not cr.records_sent:
                pending.append("Send Records (fax/send to receiving facility)")
            actions.append({
                "action": "COMPLETE_EMTALA",
                "description": f"Complete EMTALA checklist: {', '.join(pending)}",
                "pending_items": pending,
                "priority": "HIGH",
            })
        else:
            actions.append({"action": "DISPATCH_TRANSPORT", "description": "All EMTALA checks passed — ready to dispatch transport", "priority": "HIGH"})

    elif status == "TRANSPORT_DISPATCHED":
        actions.append({"action": "MONITOR", "description": "Transport is en route. Monitor for arrival.", "priority": "MEDIUM"})

    elif status == "IN_TRANSIT":
        actions.append({"action": "CONFIRM_ARRIVAL", "description": "Confirm patient arrival at receiving facility.", "priority": "HIGH"})

    elif status == "ARRIVED":
        actions.append({"action": "COMPLETE_TRANSFER", "description": "Mark transfer as completed.", "priority": "MEDIUM"})

    elif status == "COMPLETED":
        actions.append({"action": "NONE", "description": "Transfer is complete. No further action needed.", "priority": "LOW"})

    return {
        "transfer_id": transfer_id,
        "current_status": status,
        "urgency": transfer.urgency,
        "recommended_actions": actions,
    }
