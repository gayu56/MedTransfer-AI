"""
Facility Agent — Owns hospital matching, bed availability tracking, and contention resolution.
Subscribes to HOSPITAL_ACCEPTED / TRANSFER_CANCELLED to update beds in real time.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.event_bus import AgentEvent
from app.models.facility import Facility, BedAvailability
from app.models.transfer import FacilityMatch
from app.services import facility_service


SYSTEM_PROMPT = """You are the Facility Agent in a hospital transfer coordination mesh.

## Your Responsibilities
- Match and rank receiving facilities for patient transfers
- Track real-time bed availability across all hospitals
- Resolve contention when multiple transfers target the same bed
- Provide bed status summaries on demand

## Tools Available
- match_facilities: Score and rank hospitals for a transfer
- get_bed_status: Get current bed availability for a facility
- get_all_beds: Get bed availability across all facilities
- reserve_bed: Decrement bed count when a hospital accepts
- release_bed: Increment bed count when a transfer is cancelled

## Rules
- Always read bed counts from the database, never assume
- When two transfers compete for the last bed, prioritize by urgency (EMERGENT > URGENT > ROUTINE)
- Report bed contention to the orchestrator immediately
"""

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "match_facilities",
            "description": "Score and rank facilities for a transfer based on specialty, beds, distance, insurance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"},
                    "sending_facility_id": {"type": "string"},
                    "required_specialty": {"type": "string", "description": "Optional specialty needed"},
                    "required_unit_type": {"type": "string", "description": "Optional unit type needed"},
                },
                "required": ["transfer_id", "sending_facility_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bed_status",
            "description": "Get current bed availability for a specific facility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility_id": {"type": "string"},
                },
                "required": ["facility_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_beds",
            "description": "Get bed availability summary across all facilities.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reserve_bed",
            "description": "Decrement available beds by 1 at a facility after acceptance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility_id": {"type": "string"},
                },
                "required": ["facility_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "release_bed",
            "description": "Increment available beds by 1 at a facility after cancellation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "facility_id": {"type": "string"},
                },
                "required": ["facility_id"],
            },
        },
    },
]


class FacilityAgent(BaseAgent):
    """Specialist agent for facility matching and bed management."""

    @property
    def agent_name(self) -> str:
        return "FacilityAgent"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def tool_definitions(self) -> list[dict]:
        return TOOL_DEFS

    def _register_subscriptions(self) -> None:
        """React to acceptance and cancellation events to update bed counts."""
        self._bus.subscribe("HOSPITAL_ACCEPTED", self._on_hospital_accepted)
        self._bus.subscribe("TRANSFER_CANCELLED", self._on_transfer_cancelled)

    async def _on_hospital_accepted(self, event: AgentEvent) -> None:
        """When a hospital accepts — decrement its bed count."""
        facility_id = event.payload.get("facility_id")
        if facility_id:
            print(f"[{self.agent_name}] Bed decrement triggered for {facility_id}")
            # We need a DB session — use the one from payload if available
            db = event.payload.get("_db")
            if db:
                await self._reserve_bed(db, facility_id)

    async def _on_transfer_cancelled(self, event: AgentEvent) -> None:
        """When a transfer is cancelled — release the bed."""
        facility_id = event.payload.get("facility_id")
        if facility_id:
            print(f"[{self.agent_name}] Bed release triggered for {facility_id}")
            db = event.payload.get("_db")
            if db:
                await self._release_bed(db, facility_id)

    # ── Tool Execution ───────────────────────────────────────────────────

    async def execute_tool(self, tool_name: str, args: dict, db: AsyncSession) -> Any:
        if tool_name == "match_facilities":
            return await self._match_facilities(db, **args)
        elif tool_name == "get_bed_status":
            return await self._get_bed_status(db, args["facility_id"])
        elif tool_name == "get_all_beds":
            return await self._get_all_beds(db)
        elif tool_name == "reserve_bed":
            return await self._reserve_bed(db, args["facility_id"])
        elif tool_name == "release_bed":
            return await self._release_bed(db, args["facility_id"])
        return {"error": f"Unknown tool: {tool_name}"}

    # ── Direct execution methods (used by fallback and event handlers) ───

    async def _match_facilities(self, db: AsyncSession, transfer_id: str,
                                sending_facility_id: str,
                                required_specialty: str | None = None,
                                required_unit_type: str | None = None) -> dict:
        """Score and rank facilities, save matches to DB, emit event."""
        matches = await facility_service.match_facilities(
            db=db,
            transfer_id=transfer_id,
            sending_facility_id=sending_facility_id,
            required_specialty=required_specialty,
            required_unit_type=required_unit_type,
        )
        match_count = len(matches) if matches else 0

        await self.emit("FACILITIES_MATCHED", transfer_id=transfer_id, payload={
            "match_count": match_count,
            "sending_facility_id": sending_facility_id,
        })

        return {"status": "ok", "matches_found": match_count}

    async def _get_bed_status(self, db: AsyncSession, facility_id: str) -> dict:
        """Get bed availability for a single facility."""
        result = await db.execute(
            select(BedAvailability).where(BedAvailability.facility_id == facility_id)
        )
        beds = list(result.scalars().all())
        fac = await db.get(Facility, facility_id)
        return {
            "facility_id": facility_id,
            "facility_name": fac.name if fac else "Unknown",
            "units": [
                {
                    "unit_type": b.unit_type,
                    "total": b.total_beds,
                    "occupied": b.occupied_beds,
                    "available": b.available_beds,
                }
                for b in beds
            ],
            "total_available": sum(b.available_beds for b in beds),
        }

    async def _get_all_beds(self, db: AsyncSession) -> dict:
        """Get bed availability across all facilities."""
        result = await db.execute(
            select(Facility)
            .where(Facility.accepts_transfers == True)
            .options(selectinload(Facility.bed_availability))
        )
        facilities = list(result.scalars().all())
        summary = []
        for f in facilities:
            total_avail = sum(b.available_beds for b in f.bed_availability)
            summary.append({
                "facility_id": f.id,
                "name": f.name,
                "total_available": total_avail,
                "units": [
                    {"type": b.unit_type, "available": b.available_beds}
                    for b in f.bed_availability
                ],
            })
        return {"facilities": summary}

    async def _reserve_bed(self, db: AsyncSession, facility_id: str) -> dict:
        """Decrement bed count by 1 — called on acceptance."""
        beds_result = await db.execute(
            select(BedAvailability)
            .where(BedAvailability.facility_id == facility_id)
            .where(BedAvailability.occupied_beds < BedAvailability.total_beds)
            .order_by(BedAvailability.unit_type)
            .limit(1)
        )
        bed = beds_result.scalar_one_or_none()
        if bed:
            bed.occupied_beds += 1
            bed.last_updated_at = datetime.now(timezone.utc)
            await db.flush()
            await self.emit("BED_RESERVED", payload={
                "facility_id": facility_id,
                "unit_type": bed.unit_type,
                "available_after": bed.available_beds,
            })
            return {"status": "ok", "unit": bed.unit_type, "available_now": bed.available_beds}
        return {"status": "no_beds_to_reserve"}

    async def _release_bed(self, db: AsyncSession, facility_id: str) -> dict:
        """Increment bed count by 1 — called on cancellation."""
        beds_result = await db.execute(
            select(BedAvailability)
            .where(BedAvailability.facility_id == facility_id)
            .where(BedAvailability.occupied_beds > 0)
            .order_by(BedAvailability.unit_type)
            .limit(1)
        )
        bed = beds_result.scalar_one_or_none()
        if bed:
            bed.occupied_beds -= 1
            bed.last_updated_at = datetime.now(timezone.utc)
            await db.flush()
            await self.emit("BED_RELEASED", payload={
                "facility_id": facility_id,
                "unit_type": bed.unit_type,
                "available_after": bed.available_beds,
            })
            return {"status": "ok", "unit": bed.unit_type, "available_now": bed.available_beds}
        return {"status": "no_beds_to_release"}

    # ── Fallback (no LLM) ───────────────────────────────────────────────

    async def fallback(self, task: str, db: AsyncSession,
                       context: dict | None = None) -> dict:
        """Direct execution without LLM reasoning."""
        ctx = context or {}
        action = ctx.get("action", "match")

        if action == "match":
            result = await self._match_facilities(
                db,
                transfer_id=ctx["transfer_id"],
                sending_facility_id=ctx["sending_facility_id"],
                required_specialty=ctx.get("required_specialty"),
                required_unit_type=ctx.get("required_unit_type"),
            )
        elif action == "reserve_bed":
            result = await self._reserve_bed(db, ctx["facility_id"])
        elif action == "release_bed":
            result = await self._release_bed(db, ctx["facility_id"])
        elif action == "get_bed_status":
            result = await self._get_bed_status(db, ctx["facility_id"])
        elif action == "get_all_beds":
            result = await self._get_all_beds(db)
        else:
            result = {"error": f"Unknown action: {action}"}

        return {
            "response": f"[FacilityAgent] Executed {action}",
            "actions_taken": [{"agent": "FacilityAgent", "tool": action, "result_summary": str(result)[:300]}],
            "events_emitted": [],
            "result": result,
        }


# ── Singleton ────────────────────────────────────────────────────────────
facility_agent = FacilityAgent()
