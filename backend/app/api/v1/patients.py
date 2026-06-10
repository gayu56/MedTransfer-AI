from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientResponse, PatientListResponse

router = APIRouter()


@router.get("", response_model=PatientListResponse)
async def list_patients(
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Patient)
    count_query = select(func.count(Patient.id))

    if search:
        search_filter = (
            Patient.first_name.ilike(f"%{search}%")
            | Patient.last_name.ilike(f"%{search}%")
            | Patient.mrn.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.order_by(Patient.last_name).limit(limit).offset(offset))
    patients = result.scalars().all()

    return PatientListResponse(
        data=[
            PatientResponse(
                id=p.id, mrn=p.mrn, first_name=p.first_name, last_name=p.last_name,
                date_of_birth=p.date_of_birth, gender=p.gender, age=p.age,
                insurance_provider=p.insurance_provider, insurance_plan_name=p.insurance_plan_name,
                insurance_member_id=p.insurance_member_id, code_status=p.code_status,
                allergies=p.allergies or [], primary_language=p.primary_language,
                vitals=p.vitals or {}, active_conditions=p.active_conditions or [],
                current_medications=p.current_medications or [], lab_results=p.lab_results or [],
                imaging_results=p.imaging_results or [], created_at=p.created_at,
            )
            for p in patients
        ],
        total_count=total,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return PatientResponse(
        id=patient.id, mrn=patient.mrn, first_name=patient.first_name,
        last_name=patient.last_name, date_of_birth=patient.date_of_birth,
        gender=patient.gender, age=patient.age,
        insurance_provider=patient.insurance_provider,
        insurance_plan_name=patient.insurance_plan_name,
        insurance_member_id=patient.insurance_member_id,
        code_status=patient.code_status, allergies=patient.allergies or [],
        primary_language=patient.primary_language,
        vitals=patient.vitals or {}, active_conditions=patient.active_conditions or [],
        current_medications=patient.current_medications or [],
        lab_results=patient.lab_results or [], imaging_results=patient.imaging_results or [],
        created_at=patient.created_at,
    )
