"""
Inter-agent event bus for the agentic mesh.
Agents publish events and subscribe to events from other agents.
Uses async in-memory pub/sub (swap to Redis in production for multi-worker).
"""
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass
class AgentEvent:
    """An event emitted by an agent for other agents to react to."""
    event_type: str                   # e.g. "TRANSFER_CREATED", "HOSPITAL_ACCEPTED"
    source_agent: str                 # Agent that emitted the event
    transfer_id: str | None = None    # Associated transfer
    payload: dict = field(default_factory=dict)  # Event-specific data
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Type alias for event handler: async function(event) -> None
EventHandler = Callable[[AgentEvent], Coroutine[Any, Any, None]]


class EventBus:
    """Async in-memory pub/sub bus for inter-agent communication."""

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._event_log: list[AgentEvent] = []  # Full audit trail

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe an agent's handler to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to ALL events (for the orchestrator / logging)."""
        if "*" not in self._subscribers:
            self._subscribers["*"] = []
        self._subscribers["*"].append(handler)

    async def publish(self, event: AgentEvent) -> None:
        """Publish an event — all subscribed handlers are called concurrently."""
        self._event_log.append(event)
        print(f"[EVENT BUS] {event.source_agent} → {event.event_type}"
              f" (transfer={event.transfer_id})")

        handlers = self._subscribers.get(event.event_type, [])
        wildcard_handlers = self._subscribers.get("*", [])
        all_handlers = handlers + wildcard_handlers

        # Run all handlers concurrently
        if all_handlers:
            await asyncio.gather(
                *(h(event) for h in all_handlers),
                return_exceptions=True,
            )

    def get_event_log(self, transfer_id: str | None = None) -> list[AgentEvent]:
        """Get the event log, optionally filtered by transfer_id."""
        if transfer_id:
            return [e for e in self._event_log if e.transfer_id == transfer_id]
        return list(self._event_log)

    def clear_log(self) -> None:
        """Clear the event log (for testing)."""
        self._event_log.clear()


# ── Singleton event bus instance ──
event_bus = EventBus()
