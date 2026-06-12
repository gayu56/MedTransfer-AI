from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.transfer import ComplianceResponse
from app.services import compliance_service

router = APIRouter()


class ComplianceUpdateRequest(BaseModel):
    field: str
    value: bool
    consent_signer_name: str | None = None
    consent_signer_relationship: str | None = None
    certification_reason: str | None = None
    stabilization_notes: str | None = None
    transport_level_justified: str | None = None


@router.get("/{transfer_id}", response_model=ComplianceResponse)
async def get_compliance(transfer_id: str, db: AsyncSession = Depends(get_db)):
    record = await compliance_service.get_compliance(db, transfer_id)
    if not record:
        raise HTTPException(status_code=404, detail="Compliance record not found")
    return ComplianceResponse(
        id=record.id,
        mse_completed=record.mse_completed,
        stabilization_attempted=record.stabilization_attempted,
        md_certification_signed=record.md_certification_signed,
        consent_obtained=record.consent_obtained,
        receiving_facility_confirmed=record.receiving_facility_confirmed,
        transport_appropriate=record.transport_appropriate,
        records_sent=record.records_sent,
        all_checks_passed=record.all_checks_passed,
    )


@router.patch("/{transfer_id}", response_model=ComplianceResponse)
async def update_compliance(
    transfer_id: str,
    req: ComplianceUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    kwargs = {}
    if req.consent_signer_name:
        kwargs["consent_signer_name"] = req.consent_signer_name
    if req.consent_signer_relationship:
        kwargs["consent_signer_relationship"] = req.consent_signer_relationship
    if req.certification_reason:
        kwargs["certification_reason"] = req.certification_reason
    if req.stabilization_notes:
        kwargs["stabilization_notes"] = req.stabilization_notes
    if req.transport_level_justified:
        kwargs["transport_level_justified"] = req.transport_level_justified

    record = await compliance_service.update_compliance_field(
        db, transfer_id, req.field, req.value, **kwargs,
    )
    if not record:
        raise HTTPException(status_code=404, detail="Compliance record not found or invalid field")

    return ComplianceResponse(
        id=record.id,
        mse_completed=record.mse_completed,
        stabilization_attempted=record.stabilization_attempted,
        md_certification_signed=record.md_certification_signed,
        consent_obtained=record.consent_obtained,
        receiving_facility_confirmed=record.receiving_facility_confirmed,
        transport_appropriate=record.transport_appropriate,
        records_sent=record.records_sent,
        all_checks_passed=record.all_checks_passed,
    )


@router.get("/{transfer_id}/can-broadcast")
async def check_can_broadcast(transfer_id: str, db: AsyncSession = Depends(get_db)):
    """Check if pre-broadcast EMTALA items are complete before sending transfer to facilities."""
    record = await compliance_service.get_compliance(db, transfer_id)
    if not record:
        raise HTTPException(status_code=404, detail="Compliance record not found")

    can_broadcast, missing, completed = compliance_service.can_broadcast_to_facilities(record)
    return {
        "can_broadcast": can_broadcast,
        "missing_items": missing,
        "completed_items": completed,
        "message": "Ready to send transfer request to facilities" if can_broadcast else f"{len(missing)} EMTALA item(s) must be completed before contacting facilities",
    }


@router.get("/{transfer_id}/can-dispatch")
async def check_can_dispatch(transfer_id: str, db: AsyncSession = Depends(get_db)):
    record = await compliance_service.get_compliance(db, transfer_id)
    if not record:
        raise HTTPException(status_code=404, detail="Compliance record not found")

    can_dispatch, missing = compliance_service.can_dispatch_transport(record)
    return {
        "can_dispatch": can_dispatch,
        "missing_items": missing,
    }
