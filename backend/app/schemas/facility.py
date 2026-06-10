from datetime import datetime
from pydantic import BaseModel


class BedAvailabilityResponse(BaseModel):
    unit_type: str
    total_beds: int
    occupied_beds: int
    available_beds: int

    class Config:
        from_attributes = True


class CapabilityResponse(BaseModel):
    category: str
    name: str
    is_active: bool = True
    available_24_7: bool = False

    class Config:
        from_attributes = True


class FacilityResponse(BaseModel):
    id: str
    name: str
    facility_type: str
    trauma_level: str | None = None
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    transfer_center_phone: str | None = None
    accepts_transfers: bool = True
    capabilities: list[CapabilityResponse] = []
    bed_availability: list[BedAvailabilityResponse] = []
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class FacilityListResponse(BaseModel):
    data: list[FacilityResponse]
    total_count: int


class BedUpdateRequest(BaseModel):
    unit_type: str
    total_beds: int
    occupied_beds: int
