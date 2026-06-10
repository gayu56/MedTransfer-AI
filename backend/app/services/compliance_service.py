from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceRecord


async def get_compliance(db: AsyncSession, transfer_id: str) -> ComplianceRecord | None:
    result = await db.execute(
        select(ComplianceRecord).where(ComplianceRecord.transfer_id == transfer_id)
    )
    return result.scalar_one_or_none()


async def update_compliance_field(
    db: AsyncSession,
    transfer_id: str,
    field: str,
    value: bool,
    **kwargs,
) -> ComplianceRecord | None:
    record = await get_compliance(db, transfer_id)
    if not record:
        return None

    now = datetime.now(timezone.utc)
    allowed_fields = {
        "mse_completed": "mse_completed_at",
        "stabilization_attempted": None,
        "md_certification_signed": "md_certification_at",
        "consent_obtained": "consent_signed_at",
        "receiving_facility_confirmed": "receiving_confirmed_at",
        "transport_appropriate": None,
        "records_sent": "records_sent_at",
    }

    if field not in allowed_fields:
        return None

    setattr(record, field, value)
    timestamp_field = allowed_fields[field]
    if timestamp_field and value:
        setattr(record, timestamp_field, now)

    # Set additional kwargs (e.g., consent_signer_name, certification_reason)
    for k, v in kwargs.items():
        if hasattr(record, k):
            setattr(record, k, v)

    record.updated_at = now
    await db.flush()
    return record


def can_dispatch_transport(compliance: ComplianceRecord) -> tuple[bool, list[str]]:
    """Check if all compliance requirements are met for transport dispatch."""
    missing = []
    if not compliance.mse_completed:
        missing.append("Medical Screening Exam not completed")
    if not compliance.stabilization_attempted:
        missing.append("Stabilization not documented")
    if not compliance.md_certification_signed:
        missing.append("Physician certification not signed")
    if not compliance.consent_obtained:
        missing.append("Patient consent not obtained")
    if not compliance.receiving_facility_confirmed:
        missing.append("Receiving facility has not confirmed acceptance")
    if not compliance.transport_appropriate:
        missing.append("Transport appropriateness not confirmed")
    if not compliance.records_sent:
        missing.append("Medical records not prepared/sent")

    return len(missing) == 0, missing
