from pathlib import Path

from app.tools.research_tools import (
    build_tools,
    compare_sources,
    record_audit_event,
    save_report,
)


def test_save_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "app.tools.research_tools.config.reports_dir", "reports"
    )

    result = save_report(
        "Test Report",
        "# Hello"
    )

    assert "saved" in result.lower()

    assert Path(
        "reports/test_report.md"
    ).exists()


def test_save_report_rejects_empty_content(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "app.tools.research_tools.config.reports_dir", "reports"
    )

    result = save_report("Empty Report", "   ")

    assert "rejected" in result.lower()
    assert not Path("reports/empty_report.md").exists()


def test_save_report_blocks_path_traversal(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "app.tools.research_tools.config.reports_dir", "reports"
    )

    save_report("../../etc/passwd", "malicious content")

    reports_dir = Path("reports").resolve()
    saved_files = list(reports_dir.glob("*.md"))

    assert len(saved_files) == 1
    for file in saved_files:
        assert file.resolve().parent == reports_dir


def test_audit_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "app.tools.research_tools.config.reports_dir", "reports"
    )

    record_audit_event(
        "test",
        "audit working"
    )

    assert Path(
        "reports/audit_log.jsonl"
    ).exists()


def test_audit_log_rejects_empty_detail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "app.tools.research_tools.config.reports_dir", "reports"
    )

    result = record_audit_event("test", "")

    assert "rejected" in result.lower()
    assert not Path("reports/audit_log.jsonl").exists()


def test_audit_log_records_report_id(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "app.tools.research_tools.config.reports_dir", "reports"
    )

    record_audit_event("test", "correlated event", report_id="abc123")

    content = Path("reports/audit_log.jsonl").read_text(encoding="utf-8")
    assert "abc123" in content


def test_compare_sources_is_read_only():
    reports_dir = Path("reports")
    before = set(reports_dir.glob("*.md")) if reports_dir.exists() else set()

    result = compare_sources("Ippon scoring", "grip strength training")

    after = set(reports_dir.glob("*.md")) if reports_dir.exists() else set()

    assert "topic_a" in result
    assert "topic_b" in result
    assert "overlap_sources" in result
    assert "evidence_limitations" in result
    assert before == after


def test_build_tools_blocks_save_before_approval():
    tools = build_tools(approved_to_save=False)
    names = {tool.metadata.name for tool in tools}

    assert "save_report" not in names
    assert "knowledge_base_search" in names
    assert "compare_sources" in names
    assert "record_audit_event" in names


def test_build_tools_allows_save_after_approval():
    tools = build_tools(approved_to_save=True)
    names = {tool.metadata.name for tool in tools}

    assert "save_report" in names
