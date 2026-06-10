from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import transfer_service

router = APIRouter()


@router.get("/transfers")
async def get_transfer_analytics(db: AsyncSession = Depends(get_db)):
    return await transfer_service.get_transfer_analytics(db)
