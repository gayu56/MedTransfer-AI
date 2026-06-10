from datetime import datetime
from pydantic import BaseModel


class ResponseMeta(BaseModel):
    request_id: str | None = None
    timestamp: datetime | None = None


class PaginatedMeta(ResponseMeta):
    total_count: int = 0
    page_size: int = 20
    next_cursor: str | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    errors: list[ErrorDetail]
    meta: ResponseMeta | None = None
