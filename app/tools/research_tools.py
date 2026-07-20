from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from llama_index.core.tools import (
    FunctionTool,
    QueryEngineTool,
)

from app.config import config
from app.services.index_service import load_query_engine


# --------------------------------------------------
# Save Report
# --------------------------------------------------

def save_report(title: str, content: str, report_id: str | None = None) -> str:
    """
    Save a Markdown report into the restricted reports directory.
    """

    if not title.strip() or not content.strip():
        return "Save rejected: title and content must not be empty."

    reports_dir = Path(config.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(
        c for c in title.lower().replace(" ", "_")
        if c.isalnum() or c == "_"
    )

    filename = safe_name[:60] or "report"

    # Filename is derived purely from sanitized alnum/underscore characters
    # and confined to reports_dir, so it cannot escape via path traversal.
    path = reports_dir / f"{filename}.md"

    body = content
    if report_id:
        body = f"<!-- report_id: {report_id} -->\n\n{content}"

    path.write_text(
        body,
        encoding="utf-8",
    )

    return f"Report saved to {path}"


# --------------------------------------------------
# Audit Log
# --------------------------------------------------

def record_audit_event(
    action: str,
    detail: str,
    report_id: str | None = None,
) -> str:
    """
    Record important actions.
    """

    if not action.strip() or not detail.strip():
        return "Audit rejected: action and detail must not be empty."

    reports_dir = Path(config.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    log_path = reports_dir / "audit_log.jsonl"

    event = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "action": action,
        "detail": detail,
        "report_id": report_id,
    }

    with log_path.open(
        "a",
        encoding="utf-8",
    ) as file:

        file.write(
            json.dumps(event)
            + "\n"
        )

    return "Audit event recorded."


# --------------------------------------------------
# Compare Sources
# --------------------------------------------------

def compare_sources(topic_a: str, topic_b: str) -> dict:
    """
    Query the knowledge base for two topics and return a structured
    comparison. Read-only: this tool never writes to disk.
    """

    query_engine = load_query_engine()

    response_a = query_engine.query(topic_a)
    response_b = query_engine.query(topic_b)

    sources_a = {
        node.metadata.get("file_name", "unknown")
        for node in response_a.source_nodes
    }
    sources_b = {
        node.metadata.get("file_name", "unknown")
        for node in response_b.source_nodes
    }

    return {
        "topic_a": topic_a,
        "topic_b": topic_b,
        "findings_a": str(response_a),
        "findings_b": str(response_b),
        "overlap_sources": sorted(sources_a & sources_b),
        "sources_only_in_a": sorted(sources_a - sources_b),
        "sources_only_in_b": sorted(sources_b - sources_a),
        "evidence_limitations": (
            "Findings are limited to what the indexed knowledge base "
            "returned for each topic; absence of a source does not mean "
            "no evidence exists, only that it was not retrieved."
        ),
    }


# --------------------------------------------------
# Build Tools
# --------------------------------------------------

def build_tools(approved_to_save: bool = False, report_id: str | None = None):
    """
    Build the agent's tool list.

    The save_report tool is only included when approved_to_save is True,
    so an unapproved run has no capability to persist a report at all —
    this is stronger than relying on a natural-language instruction.
    """

    query_engine = load_query_engine()

    knowledge_tool = QueryEngineTool.from_defaults(
        query_engine=query_engine,
        name="knowledge_base_search",
        description=(
            "Search the JudoCoach AI knowledge base "
            "before answering factual coaching questions."
        ),
    )

    compare_tool = FunctionTool.from_defaults(
        fn=compare_sources,
        name="compare_sources",
        description=(
            "Compare evidence for two topics by querying the knowledge base "
            "twice. Returns overlap, differences, and evidence limitations. "
            "Does not write any files."
        ),
    )

    def _record_audit_event(action: str, detail: str) -> str:
        return record_audit_event(action, detail, report_id=report_id)

    audit_tool = FunctionTool.from_defaults(
        fn=_record_audit_event,
        name="record_audit_event",
        description=(
            "Record important actions "
            "in the audit log."
        ),
    )

    tools = [knowledge_tool, compare_tool, audit_tool]

    if approved_to_save:

        def _save_report(title: str, content: str) -> str:
            return save_report(title, content, report_id=report_id)

        save_tool = FunctionTool.from_defaults(
            fn=_save_report,
            name="save_report",
            description=(
                "Save an approved report as Markdown. Only call this when "
                "the user has explicitly approved saving."
            ),
        )
        tools.append(save_tool)

    return tools