"""
Outreach Agent — Owns all hospital communication: broadcast, accept/decline handling,
cancellation notifications. Emits events for other agents to react to.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.event_bus import AgentEvent
from app.models.call_log import CallLog
from app.models.transfer import TransferRequest, TransferTimeline, FacilityMatch
from app.models.facility import Facility
from app.models.compliance import ComplianceRecord
from app.services.call_service import simulate_call_outcome


SYSTEM_PROMPT = """You are the Outreach Agent in a hospital transfer coordination mesh.

## Your Responsibilities
- Broadcast transfer requests to all matched facilities simultaneously
- Handle accept/decline responses from hospitals
- Atomically lock the first accepting hospital (prevent double-acceptance)
- Send cancellation notices to all other hospitals after one accepts
- Track call outcomes and maintain call logs

## Tools Available
- broadcast_transfer: Send transfer request to all matched facilities
- cancel_other_facilities: Notify non-accepted hospitals that the transfer is filled
- get_call_history: Get call log for a transfer

## Rules
- The FIRST hospital to accept wins — use atomic locking (UPDATE WHERE status='PENDING_REVIEW')
- After locking, immediately cancel all other contacted facilities
- Emit HOSPITAL_ACCEPTED event so FacilityAgent can update beds
- Emit CANCELLATION_SENT event after notifying other hospitals
- Never accept a transfer that is already accepted
"""

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "broadcast_transfer",
            "description": "Broadcast transfer request to all matched facilities and handle responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"},
                },
                "required": ["transfer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_other_facilities",
            "description": "Send cancellation to all non-accepted facilities for a transfer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"},
                    "accepted_facility_id": {"type": "string"},
                },
                "required": ["transfer_id", "accepted_facility_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_call_history",
            "description": "Get the call log history for a transfer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"},
                },
                "required": ["transfer_id"],
            },
        },
    },
]


class OutreachAgent(BaseAgent):
    """Specialist agent for hospital outreach and broadcast communication."""

    @property
    def agent_name(self) -> str:
        return "OutreachAgent"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def tool_definitions(self) -> list[dict]:
        return TOOL_DEFS

    # ── Tool execution ───────────────────────────────────────────────────

    async def execute_tool(self, tool_name: str, args: dict, db: AsyncSession) -> Any:
        if tool_name == "broadcast_transfer":
            return await self._broadcast_transfer(db, args["transfer_id"])
        elif tool_name == "cancel_other_facilities":
            return await self._cancel_other_facilities(
                db, args["transfer_id"], args["accepted_facility_id"],
            )
        elif tool_name == "get_call_history":
            return await self._get_call_history(db, args["transfer_id"])
        return {"error": f"Unknown tool: {tool_name}"}

    # ── Broadcast: send to ALL facilities, first accept wins ─────────────

    async def _broadcast_transfer(self, db: AsyncSession, transfer_id: str) -> dict:
        """Broadcast transfer to all matched facilities. Atomic lock on first accept."""
        # Load facility matches
        matches_result = await db.execute(
            select(FacilityMatch)
            .where(FacilityMatch.transfer_id == transfer_id)
            .order_by(FacilityMatch.rank)
        )
        matches = list(matches_result.scalars().all())
        broadcastable = [m for m in matches if m.status not in ("ACCEPTED", "DECLINED", "CANCELLED")]

        # Mark all as SENT
        for match in broadcastable:
            match.status = "SENT"
            match.responded_at = None

        # Timeline: broadcast started
        db.add(TransferTimeline(
            transfer_id=transfer_id,
            event_type="BROADCAST_SENT",
            event_description=f"Transfer request broadcast to {len(broadcastable)} facilities simultaneously",
            triggered_by_system=True,
        ))
        await db.flush()

        # Emit event: broadcast started
        await self.emit("BROADCAST_STARTED", transfer_id=transfer_id, payload={
            "facility_count": len(broadcastable),
        })

        results = []
        accepted_facility = None

        # Simulate responses from each facility
        for match in broadcastable:
            facility = await db.get(Facility, match.facility_id)
            fname = facility.name if facility else "Unknown"

            # Create call log entry
            call = CallLog(
                transfer_id=transfer_id,
                facility_id=match.facility_id,
                called_by_user_id="user-sarah-01",
                notes=f"Broadcast request sent to {fname}",
                call_started_at=datetime.now(timezone.utc),
                outcome="PENDING",
                is_simulated=True,
                human_confirmed=False,
            )
            db.add(call)
            await db.flush()

            # Simulate facility's response
            sim = await simulate_call_outcome(db, transfer_id, match.facility_id)
            sim_outcome = sim.get("outcome", "NO_ANSWER")

            call.call_ended_at = datetime.now(timezone.utc)
            call.duration_seconds = sim.get("duration_seconds")
            call.notes = sim.get("notes")
            call.contact_name = sim.get("contact_name")
            call.contact_role = sim.get("contact_role")

            if sim_outcome == "ACCEPTED" and not accepted_facility:
                # ATOMIC LOCK — single UPDATE with WHERE guard
                now = datetime.now(timezone.utc)
                lock_result = await db.execute(
                    update(TransferRequest)
                    .where(TransferRequest.id == transfer_id)
                    .where(TransferRequest.status.in_(["INITIATED", "PENDING_REVIEW"]))
                    .values(
                        status="ACCEPTED",
                        receiving_facility_id=match.facility_id,
                        accepted_at=now,
                        updated_at=now,
                    )
                )
                if lock_result.rowcount == 1:
                    # Lock won — this facility is confirmed
                    accepted_facility = match
                    call.outcome = "ACCEPTED"
                    call.accepting_physician = sim.get("contact_name", "Accepting Physician")
                    call.human_confirmed = True
                    match.status = "ACCEPTED"
                    match.responded_at = now

                    # Update compliance — receiving facility confirmed
                    cr_result = await db.execute(
                        select(ComplianceRecord).where(ComplianceRecord.transfer_id == transfer_id)
                    )
                    cr = cr_result.scalar_one_or_none()
                    if cr:
                        cr.receiving_facility_confirmed = True
                        cr.receiving_confirmed_at = now

                    # Emit HOSPITAL_ACCEPTED → FacilityAgent decrements beds
                    await self.emit("HOSPITAL_ACCEPTED", transfer_id=transfer_id, payload={
                        "facility_id": match.facility_id,
                        "facility_name": fname,
                        "physician": sim.get("contact_name"),
                        "_db": db,  # Pass DB session for event handler
                    })

                    # Cancel all other facilities
                    await self._cancel_other_facilities(db, transfer_id, match.facility_id)
                else:
                    # Lock failed — race lost
                    call.outcome = "DECLINED"
                    call.notes = "Transfer already locked by another facility"
                    match.status = "DECLINED"
                    match.declined_reason = "Transfer already accepted"
                    match.responded_at = datetime.now(timezone.utc)

            elif sim_outcome == "ACCEPTED" and accepted_facility:
                accepted_fac = await db.get(Facility, accepted_facility.facility_id)
                accepted_name = accepted_fac.name if accepted_fac else "another facility"
                call.outcome = "DECLINED"
                call.notes = f"Accepted but {accepted_name} was already locked in"
                match.status = "DECLINED"
                match.declined_reason = "Another facility accepted first"
                match.responded_at = datetime.now(timezone.utc)

            elif sim_outcome == "DECLINED":
                call.outcome = "DECLINED"
                call.decline_reason = sim.get("decline_reason")
                match.status = "DECLINED"
                match.declined_reason = sim.get("decline_reason")
                match.responded_at = datetime.now(timezone.utc)
            else:
                call.outcome = sim_outcome
                match.status = "NO_RESPONSE"
                match.responded_at = datetime.now(timezone.utc)

            # Timeline per facility
            db.add(TransferTimeline(
                transfer_id=transfer_id,
                event_type=f"BROADCAST_{call.outcome}",
                event_description=f"{fname} — {call.outcome.replace('_', ' ').title()}"
                    + (f": {sim.get('notes', '')}" if sim.get('notes') else ""),
                triggered_by_system=True,
            ))

            results.append({
                "call_id": call.id,
                "facility_id": match.facility_id,
                "facility_name": fname,
                "rank": match.rank,
                "outcome": call.outcome,
                "contact_name": sim.get("contact_name"),
                "contact_role": sim.get("contact_role"),
                "notes": call.notes,
                "decline_reason": sim.get("decline_reason") if call.outcome == "DECLINED" else None,
                "is_simulated": True,
                "accepted": call.outcome == "ACCEPTED",
            })

        # Emit broadcast complete
        await self.emit("BROADCAST_COMPLETED", transfer_id=transfer_id, payload={
            "total_contacted": len(broadcastable),
            "accepted_facility": accepted_facility.facility_id if accepted_facility else None,
            "results": [{"facility": r["facility_name"], "outcome": r["outcome"]} for r in results],
        })

        await db.commit()

        return {
            "status": "broadcast_complete",
            "broadcast_count": len(broadcastable),
            "accepted": accepted_facility is not None,
            "accepted_facility": accepted_facility.facility_id if accepted_facility else None,
            "results": results,
        }

    # ── Cancel other facilities ──────────────────────────────────────────

    async def _cancel_other_facilities(self, db: AsyncSession,
                                        transfer_id: str,
                                        accepted_facility_id: str) -> dict:
        """Notify all other contacted facilities that the transfer is filled."""
        # Cancel call logs
        other_calls_result = await db.execute(
            select(CallLog)
            .where(CallLog.transfer_id == transfer_id)
            .where(CallLog.facility_id != accepted_facility_id)
            .where(CallLog.outcome.notin_(["DECLINED", "CANCELLED"]))
        )
        other_calls = list(other_calls_result.scalars().all())

        cancelled_names = []
        for call in other_calls:
            call.outcome = "CANCELLED"
            call.notes = (call.notes or "") + " | Auto-cancelled: transfer filled."
            call.updated_at = datetime.now(timezone.utc)
            fac = await db.get(Facility, call.facility_id)
            if fac:
                cancelled_names.append(fac.name)

        # Cancel facility matches
        other_matches_result = await db.execute(
            select(FacilityMatch)
            .where(FacilityMatch.transfer_id == transfer_id)
            .where(FacilityMatch.facility_id != accepted_facility_id)
            .where(FacilityMatch.status.notin_(["ACCEPTED", "DECLINED"]))
        )
        for match in other_matches_result.scalars().all():
            match.status = "CANCELLED"
            match.declined_reason = "Transfer accepted by another facility"
            match.responded_at = datetime.now(timezone.utc)

        # Timeline
        if cancelled_names:
            db.add(TransferTimeline(
                transfer_id=transfer_id,
                event_type="CANCELLATION_BROADCAST",
                event_description=f"Cancellation sent to {len(cancelled_names)} facility(ies): {', '.join(cancelled_names)}",
                triggered_by_system=True,
            ))

        await db.flush()

        await self.emit("CANCELLATION_SENT", transfer_id=transfer_id, payload={
            "cancelled_facilities": cancelled_names,
            "count": len(cancelled_names),
        })

        return {"status": "ok", "cancelled_count": len(cancelled_names), "facilities": cancelled_names}

    # ── Call history ─────────────────────────────────────────────────────

    async def _get_call_history(self, db: AsyncSession, transfer_id: str) -> dict:
        """Get all call logs for a transfer."""
        result = await db.execute(
            select(CallLog)
            .where(CallLog.transfer_id == transfer_id)
            .order_by(CallLog.created_at)
        )
        calls = list(result.scalars().all())
        return {
            "transfer_id": transfer_id,
            "total_calls": len(calls),
            "calls": [
                {
                    "id": c.id,
                    "facility_id": c.facility_id,
                    "outcome": c.outcome,
                    "contact_name": c.contact_name,
                    "notes": c.notes,
                    "created_at": str(c.created_at),
                }
                for c in calls
            ],
        }

    # ── Fallback (no LLM) ───────────────────────────────────────────────

    async def fallback(self, task: str, db: AsyncSession,
                       context: dict | None = None) -> dict:
        """Direct execution without LLM reasoning."""
        ctx = context or {}
        action = ctx.get("action", "broadcast")

        if action == "broadcast":
            result = await self._broadcast_transfer(db, ctx["transfer_id"])
        elif action == "cancel":
            result = await self._cancel_other_facilities(
                db, ctx["transfer_id"], ctx["accepted_facility_id"],
            )
        elif action == "history":
            result = await self._get_call_history(db, ctx["transfer_id"])
        else:
            result = {"error": f"Unknown action: {action}"}

        return {
            "response": f"Executed {action}",
            "actions_taken": [{"agent": "OutreachAgent", "tool": action, "result_summary": str(result)[:300]}],
            "events_emitted": [],
            "result": result,
        }


# ── Singleton ────────────────────────────────────────────────────────────
outreach_agent = OutreachAgent()
