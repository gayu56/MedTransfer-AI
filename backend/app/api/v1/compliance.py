import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.compliance import ComplianceRecord, ComplianceDocument
from app.schemas.transfer import ComplianceResponse, ComplianceDocumentResponse
from app.services import compliance_service

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "uploads" / "compliance"
ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}
DOCUMENT_TYPES = {"MD_CERTIFICATION", "CONSENT_FORM", "RECORDS_PACKET", "TRANSPORT_ORDER"}


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
    result = await db.execute(
        select(ComplianceRecord)
        .where(ComplianceRecord.transfer_id == transfer_id)
        .options(selectinload(ComplianceRecord.documents))
    )
    record = result.scalar_one_or_none()
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
        documents=[
            ComplianceDocumentResponse(
                id=doc.id,
                document_type=doc.document_type,
                file_name=doc.file_name,
                file_size_bytes=doc.file_size_bytes,
                mime_type=doc.mime_type,
                uploaded_at=doc.uploaded_at,
                download_url=f"/api/v1/compliance/{transfer_id}/documents/{doc.id}/download",
            )
            for doc in record.documents
        ],
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


# ── Document Upload Endpoints ────────────────────────────────────────────────


@router.post("/{transfer_id}/documents", response_model=ComplianceDocumentResponse)
async def upload_compliance_document(
    transfer_id: str,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a compliance document (PDF, PNG, JPG) for an EMTALA check."""
    # Validate document type
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type. Must be one of: {', '.join(DOCUMENT_TYPES)}",
        )

    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: PDF, PNG, JPG",
        )

    # Get compliance record
    record = await compliance_service.get_compliance(db, transfer_id)
    if not record:
        raise HTTPException(status_code=404, detail="Compliance record not found")

    # Create upload directory
    transfer_dir = UPLOAD_DIR / transfer_id
    transfer_dir.mkdir(parents=True, exist_ok=True)

    # Save file with unique name
    file_ext = Path(file.filename).suffix if file.filename else ".pdf"
    saved_filename = f"{document_type}_{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = transfer_dir / saved_filename

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Create DB record
    doc = ComplianceDocument(
        compliance_id=record.id,
        document_type=document_type,
        file_name=file.filename or saved_filename,
        file_path=str(file_path),
        file_size_bytes=len(contents),
        mime_type=file.content_type,
    )
    db.add(doc)
    await db.flush()

    return ComplianceDocumentResponse(
        id=doc.id,
        document_type=doc.document_type,
        file_name=doc.file_name,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        uploaded_at=doc.uploaded_at,
        download_url=f"/api/v1/compliance/{transfer_id}/documents/{doc.id}/download",
    )


@router.get("/{transfer_id}/documents", response_model=list[ComplianceDocumentResponse])
async def list_compliance_documents(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded documents for a transfer's compliance record."""
    record = await compliance_service.get_compliance(db, transfer_id)
    if not record:
        raise HTTPException(status_code=404, detail="Compliance record not found")

    result = await db.execute(
        select(ComplianceDocument)
        .where(ComplianceDocument.compliance_id == record.id)
        .order_by(ComplianceDocument.uploaded_at)
    )
    docs = list(result.scalars().all())

    return [
        ComplianceDocumentResponse(
            id=doc.id,
            document_type=doc.document_type,
            file_name=doc.file_name,
            file_size_bytes=doc.file_size_bytes,
            mime_type=doc.mime_type,
            uploaded_at=doc.uploaded_at,
            download_url=f"/api/v1/compliance/{transfer_id}/documents/{doc.id}/download",
        )
        for doc in docs
    ]


@router.get("/{transfer_id}/documents/{document_id}/download")
async def download_compliance_document(
    transfer_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a specific compliance document."""
    result = await db.execute(
        select(ComplianceDocument).where(ComplianceDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type=doc.mime_type,
    )


@router.delete("/{transfer_id}/documents/{document_id}")
async def delete_compliance_document(
    transfer_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a compliance document."""
    result = await db.execute(
        select(ComplianceDocument).where(ComplianceDocument.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    await db.delete(doc)
    await db.flush()

    return {"status": "deleted", "document_id": document_id}
