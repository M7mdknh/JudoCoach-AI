import logging
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import config
from app.models import ResearchRequest, ResearchResponse
from app.orchestrator import run_research

logger = logging.getLogger(__name__)

app = FastAPI(
    title="JudoCoach AI",
    version="1.0.0",
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
KB_EXCLUDED_FILES = {"adversarial_test.md"}


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# --------------------------------------------------
# Read-only UI support endpoints
#
# These do not change /health or /research in any way. They only expose
# data that already exists on disk (indexed documents, saved reports,
# audit log) so the frontend can show real state instead of placeholders.
# --------------------------------------------------

@app.get("/stats")
def stats():
    data_dir = Path(config.data_dir)
    reports_dir = Path(config.reports_dir)

    document_count = sum(
        1
        for path in data_dir.glob("*")
        if path.is_file() and path.name not in KB_EXCLUDED_FILES
    )

    report_count = sum(
        1 for path in reports_dir.glob("*.md")
    ) if reports_dir.exists() else 0

    audit_log_path = reports_dir / "audit_log.jsonl"
    audit_event_count = 0
    if audit_log_path.exists():
        audit_event_count = sum(
            1 for line in audit_log_path.read_text(encoding="utf-8").splitlines() if line.strip()
        )

    vector_index_available = (Path(config.storage_dir) / "docstore.json").exists()

    return {
        "documents_indexed": document_count,
        "reports_saved": report_count,
        "audit_events_logged": audit_event_count,
        "model_name": config.llm_model,
        "vector_index_available": vector_index_available,
    }


@app.get("/knowledge-base")
def knowledge_base():
    data_dir = Path(config.data_dir)
    entries = []

    for path in sorted(data_dir.glob("*.md")):
        if path.name in KB_EXCLUDED_FILES:
            continue

        text = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines()]

        title = path.stem.replace("_", " ").title()
        description = ""

        for line in lines:
            if line.startswith("# "):
                title = line.lstrip("#").strip()
                if title.lower().endswith(".md"):
                    title = title[:-3].replace("_", " ").title()
                break

        for line in lines:
            if line and not line.startswith("#"):
                description = re.sub(r"[*_`]", "", line)[:160]
                break

        entries.append({
            "file_name": path.name,
            "title": title,
            "description": description,
        })

    return {"documents": entries}


@app.get("/reports")
def list_reports():
    reports_dir = Path(config.reports_dir)
    if not reports_dir.exists():
        return {"reports": []}

    entries = []
    for path in sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        content = path.read_text(encoding="utf-8")
        report_id_match = re.match(r"<!--\s*report_id:\s*(\S+)\s*-->", content)

        entries.append({
            "name": path.stem,
            "report_id": report_id_match.group(1) if report_id_match else None,
            "saved_at": path.stat().st_mtime,
            "preview": content.replace("\n", " ")[:160],
        })

    return {"reports": entries}


@app.get("/reports/{name}")
def get_report(name: str):
    reports_dir = Path(config.reports_dir).resolve()

    safe_name = "".join(c for c in name if c.isalnum() or c == "_")
    path = (reports_dir / f"{safe_name}.md").resolve()

    if reports_dir not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")

    return {"name": safe_name, "content": path.read_text(encoding="utf-8")}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.post("/research", response_model=ResearchResponse)
async def research(
    request: ResearchRequest,
):

    try:

        outcome = await run_research(
            request.question,
            approved_to_save=not request.require_approval,
        )

        return ResearchResponse(
            status=outcome.status,
            result=outcome.result,
            report_id=outcome.report_id,
        )

    except Exception:

        logger.exception("Unhandled error while processing research request")

        raise HTTPException(
            status_code=500,
            detail="Internal error processing research request.",
        )