from fastapi import APIRouter

from app.api.v1 import transfers, patients, facilities, agent, compliance, analytics, calls

api_router = APIRouter()

api_router.include_router(transfers.router, prefix="/transfers", tags=["Transfers"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(facilities.router, prefix="/facilities", tags=["Facilities"])
api_router.include_router(agent.router, prefix="/agent", tags=["AI Agent"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(calls.router, prefix="/calls", tags=["Calls"])
