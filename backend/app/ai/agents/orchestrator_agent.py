"""
Orchestrator Agent — The brain of the agentic mesh.
Receives high-level tasks (from API or chatbot), decomposes them,
and delegates to specialist agents (Facility, Outreach, Compliance).
Listens to all events on the bus for coordination and logging.
"""
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.base_agent import BaseAgent
from app.ai.agents.event_bus import AgentEvent, event_bus
from app.ai.agents.facility_agent import facility_agent
from app.ai.agents.outreach_agent import outreach_agent
from app.ai.agents.compliance_agent import compliance_agent


SYSTEM_PROMPT = """You are the Orchestrator Agent — the central coordinator of a multi-agent mesh for hospital patient transfers.

## Your Role
- Receive high-level requests from the transfer coordinator (NP)
- Decompose requests into sub-tasks and delegate to specialist agents
- Coordinate the workflow across agents
- Report back with a unified response

## Specialist Agents You Delegate To
1. **FacilityAgent** — Hospital matching, bed availability, contention resolution
2. **OutreachAgent** — Broadcast transfer requests, handle accept/decline, send cancellations
3. **ComplianceAgent** — EMTALA enforcement, human-confirmation gates, audit trail

## Tools Available
- delegate_facility: Ask FacilityAgent to match facilities or manage beds
- delegate_outreach: Ask OutreachAgent to broadcast or cancel
- delegate_compliance: Ask ComplianceAgent to check or enforce EMTALA
- get_mesh_status: Get status of all agents and recent events

## Transfer Workflow
1. Transfer created → delegate to FacilityAgent to match hospitals
2. Ready to broadcast → delegate to OutreachAgent to contact all hospitals
3. Hospital accepts → OutreachAgent emits event → FacilityAgent updates beds → ComplianceAgent starts monitoring
4. NP completes EMTALA → delegate to ComplianceAgent to verify all gates
5. All gates passed → ComplianceAgent clears dispatch

## Rules
- Always delegate to the correct specialist — never do their work yourself
- Report agent-to-agent events in your responses for transparency
- If an agent reports an error, try to resolve it or escalate to the NP
"""

TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "delegate_facility",
            "description": "Delegate a task to the FacilityAgent (matching, beds, contention).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["match", "get_bed_status", "get_all_beds", "reserve_bed", "release_bed"],
                        "description": "Which facility action to perform",
                    },
                    "transfer_id": {"type": "string", "description": "Transfer ID (for match)"},
                    "sending_facility_id": {"type": "string", "description": "Sending facility ID (for match)"},
                    "facility_id": {"type": "string", "description": "Facility ID (for bed operations)"},
                    "required_specialty": {"type": "string"},
                    "required_unit_type": {"type": "string"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_outreach",
            "description": "Delegate a task to the OutreachAgent (broadcast, cancel, history).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["broadcast", "cancel", "history"],
                        "description": "Which outreach action to perform",
                    },
                    "transfer_id": {"type": "string"},
                    "accepted_facility_id": {"type": "string", "description": "For cancel action"},
                },
                "required": ["action", "transfer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_compliance",
            "description": "Delegate a task to the ComplianceAgent (check, enforce gate, nudge).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check", "enforce_gate", "pending", "nudge"],
                        "description": "Which compliance action to perform",
                    },
                    "transfer_id": {"type": "string"},
                },
                "required": ["action", "transfer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_mesh_status",
            "description": "Get the status of the agent mesh including recent events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string", "description": "Optional: filter events by transfer"},
                },
            },
        },
    },
]


class OrchestratorAgent(BaseAgent):
    """Central coordinator that delegates to specialist agents."""

    @property
    def agent_name(self) -> str:
        return "OrchestratorAgent"

    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT

    @property
    def tool_definitions(self) -> list[dict]:
        return TOOL_DEFS

    def _register_subscriptions(self) -> None:
        """Listen to all events for coordination logging."""
        self._bus.subscribe_all(self._on_any_event)

    async def _on_any_event(self, event: AgentEvent) -> None:
        """Log all mesh events for observability."""
        if event.source_agent != self.agent_name:
            print(f"[{self.agent_name}] Observed: {event.source_agent} → {event.event_type}")

    # ── Tool execution (delegates to specialist agents) ──────────────────

    async def execute_tool(self, tool_name: str, args: dict, db: AsyncSession) -> Any:
        if tool_name == "delegate_facility":
            return await self._delegate_facility(db, args)
        elif tool_name == "delegate_outreach":
            return await self._delegate_outreach(db, args)
        elif tool_name == "delegate_compliance":
            return await self._delegate_compliance(db, args)
        elif tool_name == "get_mesh_status":
            return self._get_mesh_status(args.get("transfer_id"))
        return {"error": f"Unknown tool: {tool_name}"}

    async def _delegate_facility(self, db: AsyncSession, args: dict) -> dict:
        """Delegate to FacilityAgent."""
        context = {
            "action": args["action"],
            "transfer_id": args.get("transfer_id", ""),
            "sending_facility_id": args.get("sending_facility_id", ""),
            "facility_id": args.get("facility_id", ""),
            "required_specialty": args.get("required_specialty"),
            "required_unit_type": args.get("required_unit_type"),
        }
        result = await facility_agent.fallback(
            f"Execute {args['action']}", db, context,
        )
        return result.get("result", result)

    async def _delegate_outreach(self, db: AsyncSession, args: dict) -> dict:
        """Delegate to OutreachAgent."""
        context = {
            "action": args["action"],
            "transfer_id": args["transfer_id"],
            "accepted_facility_id": args.get("accepted_facility_id", ""),
        }
        result = await outreach_agent.fallback(
            f"Execute {args['action']}", db, context,
        )
        return result.get("result", result)

    async def _delegate_compliance(self, db: AsyncSession, args: dict) -> dict:
        """Delegate to ComplianceAgent."""
        context = {
            "action": args["action"],
            "transfer_id": args["transfer_id"],
        }
        result = await compliance_agent.fallback(
            f"Execute {args['action']}", db, context,
        )
        return result.get("result", result)

    def _get_mesh_status(self, transfer_id: str | None = None) -> dict:
        """Get mesh event log and agent status."""
        events = event_bus.get_event_log(transfer_id)
        return {
            "agents": ["OrchestratorAgent", "FacilityAgent", "OutreachAgent", "ComplianceAgent"],
            "total_events": len(events),
            "recent_events": [
                {
                    "type": e.event_type,
                    "source": e.source_agent,
                    "transfer_id": e.transfer_id,
                    "timestamp": str(e.timestamp),
                    "payload_keys": list(e.payload.keys()),
                }
                for e in events[-20:]  # Last 20 events
            ],
        }

    # ── Fallback (no LLM) — direct delegation ───────────────────────────

    async def fallback(self, task: str, db: AsyncSession,
                       context: dict | None = None) -> dict:
        """Route to the correct agent based on context."""
        ctx = context or {}
        target = ctx.get("target_agent", "")
        action = ctx.get("action", "")

        if target == "facility":
            result = await self._delegate_facility(db, ctx)
        elif target == "outreach":
            result = await self._delegate_outreach(db, ctx)
        elif target == "compliance":
            result = await self._delegate_compliance(db, ctx)
        else:
            result = {"error": f"Unknown target agent: {target}"}

        return {
            "response": f"[OrchestratorAgent] Delegated {action} to {target}",
            "actions_taken": [{"agent": "OrchestratorAgent", "delegated_to": target, "action": action}],
            "events_emitted": [],
            "result": result,
        }


# ── Singleton ────────────────────────────────────────────────────────────
orchestrator_agent = OrchestratorAgent()
