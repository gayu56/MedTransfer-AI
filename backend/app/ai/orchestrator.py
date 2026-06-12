"""
Transfer Orchestrator Agent — ReAct pattern with OpenAI function calling.
The agent reasons about the user's request, calls tools, observes results, 
and responds with a helpful answer + actions taken.
"""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent_tools import TOOL_DEFINITIONS, execute_tool
from app.ai.sbar_generator import _get_llm_client


SYSTEM_PROMPT = """You are the IPTC Transfer Coordinator AI Agent. You help hospital transfer coordinators manage patient transfers efficiently and in compliance with EMTALA regulations.

## Your Role
- Guide coordinators through the transfer process step by step
- Use tools to look up patients, generate clinical summaries, find facilities, and track compliance
- Proactively suggest the next action based on transfer state
- Flag compliance issues and blockers

## Transfer Workflow
1. Select patient → 2. Generate SBAR → 3. Create transfer → 4. Call receiving facilities → 5. Complete EMTALA checklist → 6. Dispatch transport → 7. Monitor arrival → 8. Complete

## EMTALA Rules (CRITICAL)
- ALL 7 EMTALA items must be complete before transport dispatch
- Auto-checkable: MSE (if vitals exist), Stabilization (if treatment documented), Receiving Facility (if call accepted), Transport Level (based on urgency)
- Manual only: MD Certification (physician must sign), Patient Consent (patient/family must sign), Records Sent (must be physically sent)
- NEVER skip or bypass EMTALA requirements

## Communication Style
- Be concise and action-oriented
- Use bullet points for lists
- Always tell the coordinator what to do NEXT
- If something is blocking progress, clearly state what and how to resolve it
- Format important info in bold when appropriate

## Tool Usage
- Always look up real data — never guess patient details, transfer IDs, or facility info
- When the user mentions a patient, search for them first
- When asked about a transfer, get its current status
- Proactively run EMTALA auto-checks when appropriate
- After creating a transfer, always suggest the next step (calling facilities)
"""

MAX_TOOL_ROUNDS = 5  # Max rounds of tool calls per user message


async def run_agent(
    message: str,
    db: AsyncSession,
    session_id: str,
    transfer_id: str | None = None,
    patient_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Run the orchestrator agent. Returns:
    {
        "response": str,          # Agent's text response
        "actions_taken": [...],   # List of tools called + results summary
        "suggested_actions": [...],
        "tool_calls_made": [...], # Raw tool call details for frontend display
    }
    """
    client, model = _get_llm_client()
    if not client:
        print("[AGENT] No LLM client available — using fallback keyword matching")
        return _fallback_response(message, transfer_id, patient_id)
    print(f"[AGENT] Using LLM: {model}")

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add context about current state
    context_parts = []
    if transfer_id:
        context_parts.append(f"The user is currently viewing transfer ID: {transfer_id}")
    if patient_id:
        context_parts.append(f"The user has selected patient ID: {patient_id}")
    if context_parts:
        messages.append({"role": "system", "content": "Current context: " + ". ".join(context_parts)})

    # Add conversation history
    if conversation_history:
        for msg in conversation_history[-10:]:  # Keep last 10 messages
            messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": message})

    actions_taken = []
    tool_calls_made = []

    # ReAct loop — agent can call tools multiple times
    for round_num in range(MAX_TOOL_ROUNDS):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=2000,
            )
        except Exception as e:
            print(f"LLM call failed: {e}")
            return _fallback_response(message, transfer_id, patient_id)

        choice = response.choices[0]

        # If the model wants to call tools
        if choice.message.tool_calls:
            messages.append(choice.message)

            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                # Execute the tool
                result = await execute_tool(fn_name, fn_args, db)

                # Record the action
                tool_record = {
                    "tool": fn_name,
                    "arguments": fn_args,
                    "result_preview": result[:300] if len(result) > 300 else result,
                }
                tool_calls_made.append(tool_record)
                actions_taken.append({
                    "action": fn_name,
                    "details": _summarize_tool_result(fn_name, fn_args, result),
                })

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

            continue  # Go for another round — agent may want to call more tools

        # No tool calls — agent is ready to respond
        agent_text = choice.message.content or "I've processed your request."

        # Extract suggested actions from the response context
        suggested_actions = _extract_suggested_actions(tool_calls_made, transfer_id, patient_id)

        return {
            "response": agent_text,
            "actions_taken": actions_taken,
            "suggested_actions": suggested_actions,
            "tool_calls_made": tool_calls_made,
        }

    # If we exhausted rounds, return what we have
    return {
        "response": "I've gathered the information above. Let me know if you need anything else.",
        "actions_taken": actions_taken,
        "suggested_actions": [],
        "tool_calls_made": tool_calls_made,
    }


def _summarize_tool_result(tool_name: str, args: dict, result_json: str) -> str:
    """Create a human-readable summary of a tool call."""
    try:
        data = json.loads(result_json)
    except json.JSONDecodeError:
        return f"Called {tool_name}"

    summaries = {
        "search_patient": lambda d: f"Found {d.get('count', 0)} patient(s)" if d.get('found') else f"No patients matching '{args.get('query')}'",
        "get_patient_details": lambda d: f"Retrieved details for {d.get('name', 'patient')}",
        "generate_sbar": lambda d: f"Generated SBAR (ID: {d.get('sbar_id', '?')[:8]}…)",
        "create_transfer": lambda d: f"Created transfer {d.get('transfer_number', '?')} — {d.get('facilities_matched', 0)} facilities matched",
        "get_transfer_status": lambda d: f"Transfer {d.get('transfer_number', '?')} — {d.get('status', '?')}",
        "list_active_transfers": lambda d: f"Found {d.get('count', 0)} active transfer(s)",
        "check_emtala_compliance": lambda d: f"EMTALA: {d.get('completed', 0)}/{d.get('total', 7)} complete" + (" ✓" if d.get('all_passed') else ""),
        "run_emtala_auto_checks": lambda d: d.get('summary', 'Auto-checks run'),
        "get_facility_matches": lambda d: f"Found {d.get('count', 0)} facility matches",
        "generate_call_script": lambda d: f"Call script generated for {d.get('facility_name', 'facility')}",
        "get_next_action": lambda d: f"Next: {d.get('recommended_actions', [{}])[0].get('description', 'Check status') if d.get('recommended_actions') else 'No actions needed'}",
    }

    formatter = summaries.get(tool_name, lambda d: f"Executed {tool_name}")
    try:
        return formatter(data)
    except Exception:
        return f"Called {tool_name}"


def _extract_suggested_actions(tool_calls: list, transfer_id: str | None, patient_id: str | None) -> list:
    """Extract contextual suggested actions based on what tools were called."""
    actions = []

    tool_names = [tc["tool"] for tc in tool_calls]

    if "search_patient" in tool_names and "generate_sbar" not in tool_names:
        actions.append({"action": "GENERATE_SBAR", "label": "Generate SBAR", "data": {}})

    if "generate_sbar" in tool_names and "create_transfer" not in tool_names:
        actions.append({"action": "CREATE_TRANSFER", "label": "Create Transfer", "data": {}})

    if "create_transfer" in tool_names:
        actions.append({"action": "VIEW_TRANSFER", "label": "View Transfer", "data": {}})
        actions.append({"action": "CALL_FACILITY", "label": "Call Top Facility", "data": {}})

    if "check_emtala_compliance" in tool_names or "run_emtala_auto_checks" in tool_names:
        actions.append({"action": "RUN_AUTO_CHECKS", "label": "Run Auto-Checks", "data": {}})

    if transfer_id and not actions:
        actions.append({"action": "CHECK_STATUS", "label": "Check Status", "data": {"transfer_id": transfer_id}})
        actions.append({"action": "CHECK_EMTALA", "label": "Check EMTALA", "data": {"transfer_id": transfer_id}})

    return actions


def _fallback_response(message: str, transfer_id: str | None, patient_id: str | None) -> dict:
    """Fallback when no LLM is available — basic keyword matching."""
    msg = message.lower().strip()

    # Check specific multi-word / contextual phrases FIRST (before generic keywords)
    if any(kw in msg for kw in ["active transfer", "show transfer", "list transfer", "status", "dashboard", "active", "ongoing", "pending"]):
        text = ("Here's how to view active transfers:\n"
                "• Go to the **Dashboard** to see all active transfers\n"
                "• Or tell me a **transfer number** (e.g. TR-20260610-xxxx) to look up a specific one\n\n"
                "You can also click **Transfers** in the sidebar.")
    elif any(kw in msg for kw in ["emtala", "compliance", "checklist"]):
        text = ("EMTALA requires all 7 items before transport:\n"
                "✅ Auto-verified: Medical Screening Exam, Stabilization\n"
                "✋ Manual: MD Certification, Patient Consent, Receiving Facility Confirmed, Transport Appropriate, Records Sent\n\n"
                "Open a transfer detail page to see the compliance checklist.")
    elif any(kw in msg for kw in ["sbar", "summary", "clinical"]):
        text = ("I can generate an SBAR clinical summary. To do this:\n"
                "1. Go to **New Transfer**\n"
                "2. Select a patient and fill in transfer details\n"
                "3. Click **Generate SBAR** on Step 3\n\n"
                "Or tell me the **patient name** and I'll help you start.")
    elif any(kw in msg for kw in ["call", "phone", "auto-call", "auto call"]):
        text = ("To call facilities:\n"
                "1. Open the **Transfer Detail** page for your transfer\n"
                "2. Scroll to the **Call Center** panel\n"
                "3. Click **Auto-Call Facilities** to have AI recommend a facility\n"
                "4. Then **confirm acceptance** with the accepting physician's name\n\n"
                "Remember: AI recommends, but a real clinician must confirm.")
    elif any(kw in msg for kw in ["facility", "hospital", "bed", "match"]):
        text = ("Facility matching happens automatically when you create a transfer.\n"
                "Facilities are ranked by:\n"
                "• **Specialty match** (30%) — does the facility have the needed capability?\n"
                "• **Bed availability** (25%) — are beds open in the right unit?\n"
                "• **Distance** (15%) — proximity to sending facility\n"
                "• **Insurance** (15%) — coverage compatibility\n"
                "• **History** (10%) — past acceptance rates")
    elif any(kw in msg for kw in ["transfer", "send", "move", "start", "new", "create", "initiate"]):
        text = ("I can help you start a transfer. Please tell me:\n"
                "1. **Patient name** or MRN\n"
                "2. **Reason** for transfer\n"
                "3. **Urgency** level (Emergent/Urgent/Routine)\n\n"
                "Or go to **New Transfer** in the sidebar to begin.")
    elif any(kw in msg for kw in ["help", "what can you do", "hi", "hello", "hey"]):
        text = ("👋 I'm the **MedTransfer AI Assistant**. I can help with:\n\n"
                "• **Start a transfer** — search patients, generate SBAR, create transfer\n"
                "• **Show active transfers** — view ongoing transfers and their status\n"
                "• **Find facilities** — match and call receiving hospitals\n"
                "• **Check compliance** — EMTALA checklist status\n"
                "• **Auto-call facilities** — AI-powered facility outreach\n\n"
                "What would you like to do?")
    else:
        text = ("I'm the **MedTransfer AI Assistant**. I can:\n"
                "• **Start a transfer** — search patients, generate SBAR, create transfer\n"
                "• **Show active transfers** — view ongoing transfers\n"
                "• **Find facilities** — match and call receiving hospitals\n"
                "• **Check compliance** — EMTALA checklist status\n"
                "• **Auto-call facilities** — AI-powered facility outreach\n\n"
                "Try saying: *\"Show active transfers\"* or *\"Start a new transfer\"*")

    return {
        "response": text,
        "actions_taken": [],
        "suggested_actions": [],
        "tool_calls_made": [],
    }
