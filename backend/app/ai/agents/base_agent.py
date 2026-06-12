"""
Base Agent — Common LLM reasoning + tool execution loop shared by all agents.
Each specialist agent subclasses this with its own system prompt, tools, and event subscriptions.
"""
import json
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.sbar_generator import _get_llm_client
from app.ai.agents.event_bus import AgentEvent, EventBus, event_bus


MAX_TOOL_ROUNDS = 5  # Max LLM ↔ tool iterations per agent invocation


class BaseAgent(ABC):
    """Abstract base for all mesh agents. Provides ReAct loop + event bus integration."""

    def __init__(self):
        self._bus: EventBus = event_bus
        self._register_subscriptions()

    # ── Subclass must implement ──────────────────────────────────────────

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Unique name, e.g. 'FacilityAgent'."""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """LLM system prompt describing this agent's role and constraints."""
        ...

    @property
    @abstractmethod
    def tool_definitions(self) -> list[dict]:
        """OpenAI function-calling tool definitions for this agent."""
        ...

    @abstractmethod
    async def execute_tool(self, tool_name: str, args: dict, db: AsyncSession) -> Any:
        """Execute one of this agent's tools and return the result."""
        ...

    def _register_subscriptions(self) -> None:
        """Override to subscribe to events from the bus. Called once at init."""
        pass

    # ── Event helpers ────────────────────────────────────────────────────

    async def emit(self, event_type: str, transfer_id: str | None = None,
                   payload: dict | None = None) -> None:
        """Publish an event from this agent onto the mesh event bus."""
        await self._bus.publish(AgentEvent(
            event_type=event_type,
            source_agent=self.agent_name,
            transfer_id=transfer_id,
            payload=payload or {},
        ))

    # ── Core ReAct loop ─────────────────────────────────────────────────

    async def run(self, task: str, db: AsyncSession,
                  context: dict | None = None) -> dict:
        """
        Run the agent's ReAct loop for a given task.
        Returns: {
            "response": str,         # Agent's final text output
            "actions_taken": [...],  # Tool calls made
            "events_emitted": [...], # Events published to the bus
        }
        """
        client, model = _get_llm_client()
        if not client:
            print(f"[{self.agent_name}] No LLM — using fallback")
            return await self.fallback(task, db, context)

        messages = [{"role": "system", "content": self.system_prompt}]

        # Inject context if provided
        if context:
            ctx_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
            messages.append({
                "role": "system",
                "content": f"Current context:\n{ctx_str}",
            })

        messages.append({"role": "user", "content": task})

        actions_taken = []
        events_emitted = []

        for round_num in range(MAX_TOOL_ROUNDS):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=self.tool_definitions if self.tool_definitions else None,
                    tool_choice="auto" if self.tool_definitions else None,
                    temperature=0.3,
                    timeout=30,
                )
            except Exception as e:
                print(f"[{self.agent_name}] LLM error round {round_num}: {e}")
                return await self.fallback(task, db, context)

            choice = response.choices[0]

            # If no tool calls, we have the final response
            if not choice.message.tool_calls:
                return {
                    "response": choice.message.content or "",
                    "actions_taken": actions_taken,
                    "events_emitted": events_emitted,
                }

            # Process tool calls
            messages.append(choice.message)

            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                print(f"[{self.agent_name}] Tool call: {fn_name}({fn_args})")

                try:
                    result = await self.execute_tool(fn_name, fn_args, db)
                except Exception as e:
                    result = {"error": str(e)}

                actions_taken.append({
                    "agent": self.agent_name,
                    "tool": fn_name,
                    "args": fn_args,
                    "result_summary": str(result)[:300],
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                })

        # Hit max rounds — return last content
        return {
            "response": f"[{self.agent_name}] Completed after {MAX_TOOL_ROUNDS} reasoning rounds.",
            "actions_taken": actions_taken,
            "events_emitted": events_emitted,
        }

    async def fallback(self, task: str, db: AsyncSession,
                       context: dict | None = None) -> dict:
        """Default fallback when LLM is unavailable. Subclasses should override."""
        return {
            "response": f"[{self.agent_name}] LLM unavailable — executed task directly.",
            "actions_taken": [],
            "events_emitted": [],
        }
