"""
Compliance Agent — Owns EMTALA enforcement, human-confirmation gates, and audit trail.
Listens for HOSPITAL_ACCEPTED to start monitoring compliance progress.
Hard-blocks transport dispatch if any of the 4 human-confirmed fields are False.
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.event_bus import AgentEvent
from app.models.compliance import ComplianceRecord
from app.models.transfer import TransferRequest, TransferTimeline


SYSTEM_PROMPT = """You are the Compliance Agent in a hospital transfer coordination mesh.

## Your Responsibilities
- Enforce EMTALA (Emergency Medical Treatment and Labor Act) compliance for every transfer
- Track 4 HUMAN-CONFIRMED gates that must ALL be True before transport dispatch:
  1. mse_completed — Medical Screening Exam performed
  2. patient_stabilized (stabilization_attempted) — Patient stabilization documented
  3. md_certification_signed — Physician certification signed by MD
  4. patient_consent_obtained (consent_obtained) — Patient/family consent obtained
- HARD-BLOCK transport dispatch if ANY gate is False — no exceptions, no overrides
- Monitor compliance progress and proactively nudge when items are stale
- Maintain audit trail of all compliance state changes

## Tools Available
- check_compliance: Get current EMTALA compliance status for a transfer
- enforce_dispatch_gate: Check if transport dispatch is allowed (returns hard-block if not)
- get_pending_items: List which EMTALA items are still pending
- nudge_compliance: Generate a reminder for overdue compliance items

## Rules
- NEVER auto-set any of the 4 human-confirmed gates — they require explicit human action
- receiving_facility_confirmed, transport_appropriate, and records_sent can be system-set
- Always return specific, actionable messages about what's missing
- When a transfer has been ACCEPTED for >15 minutes with incomplete compliance, proactively nudge
"""

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "check_compliance",
            "description": "Get full EMTALA compliance status for a transfer.",
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
            "name": "enforce_dispatch_gate",
            "description": "Check if transport dispatch is allowed. Returns hard-block error if EMTALA incomplete.",
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
            "name": "get_pending_items",
            "description": "List all pending EMTALA compliance items for a transfer.",
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
            "name": "nudge_compliance",
            "description": "Generate a proactive reminder for overdue compliance items.",
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


# The 4 human-confirmed gates — these can NEVER be auto-set
HUMAN_GATES = [
    {"field": "mse_completed", "label": "Medical Screening Exam"},
    {"field": "stabilization_attempted", "label": "Patient Stabilization"},
    {"field": "md_certification_signed", "label": "MD Certification Signed"},
    {"field": "consent_obtained", "label": "Patient Consent Obtained"},
]

# Additional system-managed fields
SYSTEM_FIELDS = [
    {"field": "receiving_facility_confirmed", "label": "Receiving Facility Confirmed"},
    {"field": "transport_appropriate", "label": "Transport Appropriate"},
    {"field": "records_sent", "label": "Records Sent"},
]


class ComplianceAgent(BaseAgent):
    """Specialist agent for EMTALA compliance enforcement."""

    @property
    def agent_name(self) -> str:
        return "ComplianceAgent"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def tool_definitions(self) -> list[dict]:
        return TOOL_DEFS

    def _register_subscriptions(self) -> None:
        """Start monitoring compliance when a hospital accepts."""
        self._bus.subscribe("HOSPITAL_ACCEPTED", self._on_hospital_accepted)

    async def _on_hospital_accepted(self, event: AgentEvent) -> None:
        """When a hospital accepts, emit a reminder about pending EMTALA items."""
        transfer_id = event.transfer_id
        print(f"[{self.agent_name}] Monitoring EMTALA for transfer {transfer_id}")
        await self.emit("COMPLIANCE_MONITORING_STARTED", transfer_id=transfer_id, payload={
            "message": "Hospital accepted — EMTALA compliance monitoring active. 4 human gates must be completed before transport dispatch.",
        })

    # ── Tool execution ───────────────────────────────────────────────────

    async def execute_tool(self, tool_name: str, args: dict, db: AsyncSession) -> Any:
        if tool_name == "check_compliance":
            return await self._check_compliance(db, args["transfer_id"])
        elif tool_name == "enforce_dispatch_gate":
            return await self._enforce_dispatch_gate(db, args["transfer_id"])
        elif tool_name == "get_pending_items":
            return await self._get_pending_items(db, args["transfer_id"])
        elif tool_name == "nudge_compliance":
            return await self._nudge_compliance(db, args["transfer_id"])
        return {"error": f"Unknown tool: {tool_name}"}

    # ── Core compliance methods ──────────────────────────────────────────

    async def _check_compliance(self, db: AsyncSession, transfer_id: str) -> dict:
        """Get full compliance status including human gates and system fields."""
        cr = await self._get_record(db, transfer_id)
        if not cr:
            return {"error": "No compliance record found"}

        human_status = []
        for gate in HUMAN_GATES:
            done = getattr(cr, gate["field"], False)
            human_status.append({
                "field": gate["field"],
                "label": gate["label"],
                "completed": done,
                "requires_human_action": True,
            })

        system_status = []
        for field in SYSTEM_FIELDS:
            done = getattr(cr, field["field"], False)
            system_status.append({
                "field": field["field"],
                "label": field["label"],
                "completed": done,
                "requires_human_action": False,
            })

        all_passed = cr.all_checks_passed
        human_gates_passed = all(getattr(cr, g["field"], False) for g in HUMAN_GATES)

        return {
            "transfer_id": transfer_id,
            "human_gates": human_status,
            "system_fields": system_status,
            "human_gates_passed": human_gates_passed,
            "all_checks_passed": all_passed,
            "can_dispatch": all_passed,
        }

    async def _enforce_dispatch_gate(self, db: AsyncSession, transfer_id: str) -> dict:
        """HARD-BLOCK check for transport dispatch. Returns error if any gate is False."""
        cr = await self._get_record(db, transfer_id)
        if not cr:
            return {"allowed": False, "error": "No compliance record found"}

        missing = []
        for gate in HUMAN_GATES:
            if not getattr(cr, gate["field"], False):
                missing.append(gate["label"])

        for field in SYSTEM_FIELDS:
            if not getattr(cr, field["field"], False):
                missing.append(field["label"])

        if missing:
            await self.emit("DISPATCH_BLOCKED", transfer_id=transfer_id, payload={
                "missing_items": missing,
                "message": f"EMTALA HARD STOP: {len(missing)} item(s) incomplete",
            })
            return {
                "allowed": False,
                "hard_stop": True,
                "missing_items": missing,
                "message": f"EMTALA HARD STOP: Cannot dispatch transport. Missing: {'; '.join(missing)}",
            }

        await self.emit("DISPATCH_CLEARED", transfer_id=transfer_id)
        return {"allowed": True, "message": "All EMTALA checks passed — transport dispatch authorized."}

    async def _get_pending_items(self, db: AsyncSession, transfer_id: str) -> dict:
        """List only the pending items."""
        cr = await self._get_record(db, transfer_id)
        if not cr:
            return {"error": "No compliance record found"}

        pending = []
        for gate in HUMAN_GATES:
            if not getattr(cr, gate["field"], False):
                pending.append({"field": gate["field"], "label": gate["label"], "type": "human"})
        for field in SYSTEM_FIELDS:
            if not getattr(cr, field["field"], False):
                pending.append({"field": field["field"], "label": field["label"], "type": "system"})

        return {
            "transfer_id": transfer_id,
            "pending_count": len(pending),
            "pending_items": pending,
        }

    async def _nudge_compliance(self, db: AsyncSession, transfer_id: str) -> dict:
        """Generate a proactive nudge for overdue compliance items."""
        pending = await self._get_pending_items(db, transfer_id)
        if pending.get("pending_count", 0) == 0:
            return {"message": "All compliance items complete — no nudge needed."}

        # Get transfer to check how long it's been accepted
        tr_result = await db.execute(
            select(TransferRequest).where(TransferRequest.id == transfer_id)
        )
        transfer = tr_result.scalar_one_or_none()

        elapsed_msg = ""
        if transfer and transfer.accepted_at:
            elapsed = (datetime.now(timezone.utc) - transfer.accepted_at).total_seconds() / 60
            elapsed_msg = f" Transfer accepted {elapsed:.0f} minutes ago."

        human_pending = [p for p in pending["pending_items"] if p["type"] == "human"]
        nudge_items = [p["label"] for p in human_pending]

        nudge = (
            f"[ComplianceAgent] EMTALA REMINDER:{elapsed_msg} "
            f"{len(nudge_items)} human action(s) still required: {', '.join(nudge_items)}. "
            f"Transport CANNOT be dispatched until all are completed."
        )

        # Log nudge as timeline event
        db.add(TransferTimeline(
            transfer_id=transfer_id,
            event_type="COMPLIANCE_NUDGE",
            event_description=nudge,
            triggered_by_system=True,
        ))
        await db.flush()

        await self.emit("COMPLIANCE_NUDGE", transfer_id=transfer_id, payload={
            "nudge_message": nudge,
            "pending_items": nudge_items,
        })

        return {"nudge_sent": True, "message": nudge}

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _get_record(self, db: AsyncSession, transfer_id: str) -> ComplianceRecord | None:
        result = await db.execute(
            select(ComplianceRecord).where(ComplianceRecord.transfer_id == transfer_id)
        )
        return result.scalar_one_or_none()

    # ── Fallback (no LLM) ───────────────────────────────────────────────

    async def fallback(self, task: str, db: AsyncSession,
                       context: dict | None = None) -> dict:
        """Direct execution without LLM reasoning."""
        ctx = context or {}
        action = ctx.get("action", "check")

        if action == "check":
            result = await self._check_compliance(db, ctx["transfer_id"])
        elif action == "enforce_gate":
            result = await self._enforce_dispatch_gate(db, ctx["transfer_id"])
        elif action == "pending":
            result = await self._get_pending_items(db, ctx["transfer_id"])
        elif action == "nudge":
            result = await self._nudge_compliance(db, ctx["transfer_id"])
        else:
            result = {"error": f"Unknown action: {action}"}

        return {
            "response": f"[ComplianceAgent] Executed {action}",
            "actions_taken": [{"agent": "ComplianceAgent", "tool": action, "result_summary": str(result)[:300]}],
            "events_emitted": [],
            "result": result,
        }


# ── Singleton ────────────────────────────────────────────────────────────
compliance_agent = ComplianceAgent()
