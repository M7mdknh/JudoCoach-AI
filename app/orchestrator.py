from __future__ import annotations

import uuid
from dataclasses import dataclass

from llama_index.core.agent.workflow import ToolCallResult

from app.agents.research_agent import build_agent
from app.config import config


@dataclass
class ResearchResult:
    status: str
    result: str
    report_id: str


async def run_research(question: str, approved_to_save: bool = False) -> ResearchResult:
    if not question or not question.strip():
        return ResearchResult(
            status="failed",
            result="Research objective must not be empty.",
            report_id="",
        )

    report_id = uuid.uuid4().hex[:8]

    agent = build_agent(approved_to_save=approved_to_save, report_id=report_id)

    approval_instruction = (
        "The user has approved saving the final report. The save_report "
        "tool is available to you."
        if approved_to_save
        else "The user has NOT approved saving a report. The save_report "
        "tool is not available to you in this run. Return a draft and "
        "explicitly ask for approval."
    )

    prompt = f"""
Research objective: {question}

Execution constraint: {approval_instruction}

Use the available tools and produce an evidence-grounded response. Always
search the knowledge base before making factual claims.
"""

    handler = agent.run(user_msg=prompt)

    tool_call_count = 0
    bounded_execution_triggered = False

    async for event in handler.stream_events():
        if isinstance(event, ToolCallResult):
            tool_call_count += 1
            if tool_call_count > config.max_tool_calls:
                bounded_execution_triggered = True
                await handler.cancel_run()
                break

    if bounded_execution_triggered:
        return ResearchResult(
            status="failed",
            result=(
                f"Execution stopped: exceeded the maximum of "
                f"{config.max_tool_calls} tool calls for a single request."
            ),
            report_id=report_id,
        )

    try:
        result = await handler
    except Exception as exc:  # noqa: BLE001 - surfaced as a failed status, not raised
        return ResearchResult(
            status="failed",
            result=f"Research run failed: {exc}",
            report_id=report_id,
        )

    status = "approved" if approved_to_save else "awaiting_approval"

    return ResearchResult(
        status=status,
        result=str(result),
        report_id=report_id,
    )
