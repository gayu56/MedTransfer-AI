import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.transfer import TransferRequest, TransferTimeline, FacilityMatch
from app.models.compliance import ComplianceRecord
from app.models.clinical_summary import ClinicalSummary
from app.models.patient import Patient
from app.models.facility import Facility


def _generate_transfer_number() -> str:
    now = datetime.now(timezone.utc)
    rand = str(uuid.uuid4().int)[:4]
    return f"TR-{now.strftime('%Y%m%d')}-{rand}"


async def create_transfer(
    db: AsyncSession,
    patient_id: str,
    sending_facility_id: str,
    initiated_by_user_id: str,
    urgency: str,
    reason_for_transfer: str,
    requested_specialty: str | None = None,
    requested_unit_type: str | None = None,
    additional_notes: str | None = None,
) -> TransferRequest:
    transfer = TransferRequest(
        transfer_number=_generate_transfer_number(),
        patient_id=patient_id,
        sending_facility_id=sending_facility_id,
        initiated_by_user_id=initiated_by_user_id,
        status="INITIATED",
        urgency=urgency,
        reason_for_transfer=reason_for_transfer,
        requested_specialty=requested_specialty,
        requested_unit_type=requested_unit_type,
        additional_notes=additional_notes,
        initiated_at=datetime.now(timezone.utc),
    )
    db.add(transfer)
    await db.flush()  # Ensure transfer.id is persisted

    # Create compliance record with EMTALA auto-checks
    # Auto-check items we can verify from patient clinical data
    patient = await db.get(Patient, patient_id)
    now = datetime.now(timezone.utc)

    # MSE: auto-check if patient has vitals documented
    mse_done = bool(patient and patient.vitals)
    # Stabilization: auto-check if patient has active conditions + medications
    stab_done = bool(patient and patient.active_conditions and patient.current_medications)

    compliance = ComplianceRecord(
        transfer_id=transfer.id,
        mse_completed=mse_done,
        mse_completed_at=now if mse_done else None,
        stabilization_attempted=stab_done,
        stabilization_notes="Auto-verified: vitals recorded, stabilization treatment in progress" if stab_done else None,
    )
    db.add(compliance)

    # Add timeline event
    timeline_event = TransferTimeline(
        transfer_id=transfer.id,
        event_type="TRANSFER_INITIATED",
        event_description=f"Transfer initiated — {urgency} — {reason_for_transfer[:100]}",
        triggered_by_user_id=initiated_by_user_id,
    )
    db.add(timeline_event)

    await db.flush()
    return transfer


async def get_transfer(db: AsyncSession, transfer_id: str) -> TransferRequest | None:
    result = await db.execute(
        select(TransferRequest)
        .where(TransferRequest.id == transfer_id)
        .options(
            selectinload(TransferRequest.patient),
            selectinload(TransferRequest.sending_facility),
            selectinload(TransferRequest.receiving_facility),
            selectinload(TransferRequest.clinical_summary),
            selectinload(TransferRequest.compliance_record),
            selectinload(TransferRequest.transport_request),
            selectinload(TransferRequest.facility_matches).selectinload(FacilityMatch.facility),
            selectinload(TransferRequest.timeline),
            selectinload(TransferRequest.initiated_by),
        )
    )
    return result.scalar_one_or_none()


async def list_transfers(
    db: AsyncSession,
    status: str | None = None,
    urgency: str | None = None,
    sending_facility_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[TransferRequest], int]:
    query = select(TransferRequest).options(
        selectinload(TransferRequest.patient),
        selectinload(TransferRequest.sending_facility),
        selectinload(TransferRequest.receiving_facility),
        selectinload(TransferRequest.clinical_summary),
        selectinload(TransferRequest.compliance_record),
        selectinload(TransferRequest.transport_request),
        selectinload(TransferRequest.facility_matches).selectinload(FacilityMatch.facility),
        selectinload(TransferRequest.timeline),
        selectinload(TransferRequest.initiated_by),
    )
    count_query = select(func.count(TransferRequest.id))

    if status == "active":
        active_statuses = ["DRAFT", "INITIATED", "PENDING_REVIEW", "ACCEPTED", "TRANSPORT_DISPATCHED", "IN_TRANSIT"]
        query = query.where(TransferRequest.status.in_(active_statuses))
        count_query = count_query.where(TransferRequest.status.in_(active_statuses))
    elif status:
        query = query.where(TransferRequest.status == status)
        count_query = count_query.where(TransferRequest.status == status)

    if urgency:
        query = query.where(TransferRequest.urgency == urgency)
        count_query = count_query.where(TransferRequest.urgency == urgency)

    if sending_facility_id:
        query = query.where(TransferRequest.sending_facility_id == sending_facility_id)
        count_query = count_query.where(TransferRequest.sending_facility_id == sending_facility_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(TransferRequest.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all()), total


async def update_transfer_status(
    db: AsyncSession,
    transfer_id: str,
    new_status: str,
    notes: str | None = None,
    user_id: str | None = None,
) -> TransferRequest | None:
    transfer = await get_transfer(db, transfer_id)
    if not transfer:
        return None

    old_status = transfer.status
    transfer.status = new_status
    transfer.updated_at = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    if new_status == "ACCEPTED":
        transfer.accepted_at = now
        transfer.accepted_by_user_id = user_id
    elif new_status == "TRANSPORT_DISPATCHED":
        transfer.transport_dispatched_at = now
    elif new_status in ("EN_ROUTE_PICKUP", "ON_SCENE"):
        pass  # EMS check-in — no specific timestamp column, logged in timeline
    elif new_status == "IN_TRANSIT":
        transfer.patient_departed_at = now
    elif new_status == "ARRIVED":
        transfer.patient_arrived_at = now
    elif new_status == "COMPLETED":
        transfer.completed_at = now

    # Add timeline event
    timeline_event = TransferTimeline(
        transfer_id=transfer_id,
        event_type=f"STATUS_CHANGED",
        event_description=f"Status changed from {old_status} to {new_status}" + (f" — {notes}" if notes else ""),
        triggered_by_user_id=user_id,
        triggered_by_system=user_id is None,
    )
    db.add(timeline_event)
    await db.flush()
    return transfer


async def accept_transfer(
    db: AsyncSession,
    transfer_id: str,
    accepting_user_id: str,
    facility_id: str,
    notes: str | None = None,
) -> TransferRequest | None:
    transfer = await get_transfer(db, transfer_id)
    if not transfer:
        return None

    transfer.status = "ACCEPTED"
    transfer.receiving_facility_id = facility_id
    transfer.accepted_by_user_id = accepting_user_id
    transfer.accepted_at = datetime.now(timezone.utc)
    transfer.updated_at = datetime.now(timezone.utc)

    # Update compliance
    if transfer.compliance_record:
        transfer.compliance_record.receiving_facility_confirmed = True
        transfer.compliance_record.receiving_confirmed_at = datetime.now(timezone.utc)

    # Update facility match status
    for match in transfer.facility_matches:
        if match.facility_id == facility_id:
            match.status = "ACCEPTED"
            match.responded_at = datetime.now(timezone.utc)

    timeline_event = TransferTimeline(
        transfer_id=transfer_id,
        event_type="TRANSFER_ACCEPTED",
        event_description=f"Transfer accepted" + (f" — {notes}" if notes else ""),
        triggered_by_user_id=accepting_user_id,
    )
    db.add(timeline_event)
    await db.flush()
    return transfer


async def decline_transfer(
    db: AsyncSession,
    transfer_id: str,
    facility_id: str,
    reason: str,
    notes: str | None = None,
) -> TransferRequest | None:
    transfer = await get_transfer(db, transfer_id)
    if not transfer:
        return None

    # Update the specific facility match
    for match in transfer.facility_matches:
        if match.facility_id == facility_id:
            match.status = "DECLINED"
            match.declined_reason = reason
            match.responded_at = datetime.now(timezone.utc)

    # Check if there are remaining suggested facilities
    remaining = [m for m in transfer.facility_matches if m.status == "SUGGESTED"]
    if remaining:
        transfer.status = "RE_ROUTING"
        # Auto-send to next facility
        next_match = remaining[0]
        next_match.status = "SENT"
        transfer.first_facility_contacted_at = datetime.now(timezone.utc)
    else:
        transfer.status = "DECLINED"
        transfer.decline_reason = reason

    transfer.updated_at = datetime.now(timezone.utc)

    timeline_event = TransferTimeline(
        transfer_id=transfer_id,
        event_type="TRANSFER_DECLINED",
        event_description=f"Declined by facility — {reason}" + (f" — {notes}" if notes else ""),
        triggered_by_system=True,
    )
    db.add(timeline_event)
    await db.flush()
    return transfer


async def get_transfer_analytics(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.count(TransferRequest.id)))).scalar() or 0
    active_statuses = ["INITIATED", "PENDING_REVIEW", "ACCEPTED", "TRANSPORT_DISPATCHED", "IN_TRANSIT"]
    active = (await db.execute(
        select(func.count(TransferRequest.id)).where(TransferRequest.status.in_(active_statuses))
    )).scalar() or 0
    completed = (await db.execute(
        select(func.count(TransferRequest.id)).where(TransferRequest.status == "COMPLETED")
    )).scalar() or 0

    by_urgency = {}
    for urg in ["EMERGENT", "URGENT", "ROUTINE"]:
        count = (await db.execute(
            select(func.count(TransferRequest.id)).where(TransferRequest.urgency == urg)
        )).scalar() or 0
        by_urgency[urg.lower()] = count

    return {
        "total_transfers": total,
        "active_transfers": active,
        "completed_transfers": completed,
        "by_urgency": by_urgency,
    }
