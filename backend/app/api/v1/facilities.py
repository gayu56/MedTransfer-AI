from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.facility import FacilityResponse, FacilityListResponse, BedAvailabilityResponse, CapabilityResponse
from app.services import facility_service

router = APIRouter()


def _build_facility_response(f) -> FacilityResponse:
    return FacilityResponse(
        id=f.id, name=f.name, facility_type=f.facility_type,
        trauma_level=f.trauma_level, address_line1=f.address_line1,
        city=f.city, state=f.state, zip_code=f.zip_code,
        latitude=f.latitude, longitude=f.longitude,
        phone=f.phone, transfer_center_phone=f.transfer_center_phone,
        accepts_transfers=f.accepts_transfers,
        capabilities=[
            CapabilityResponse(
                category=c.category, name=c.name,
                is_active=c.is_active, available_24_7=c.available_24_7,
            ) for c in (f.capabilities or [])
        ],
        bed_availability=[
            BedAvailabilityResponse(
                unit_type=b.unit_type, total_beds=b.total_beds,
                occupied_beds=b.occupied_beds, available_beds=b.available_beds,
            ) for b in (f.bed_availability or [])
        ],
        created_at=f.created_at,
    )


@router.get("", response_model=FacilityListResponse)
async def list_facilities(
    accepts_transfers: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    facilities = await facility_service.list_facilities(db, accepts_transfers)
    return FacilityListResponse(
        data=[_build_facility_response(f) for f in facilities],
        total_count=len(facilities),
    )


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(facility_id: str, db: AsyncSession = Depends(get_db)):
    facility = await facility_service.get_facility(db, facility_id)
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return _build_facility_response(facility)
