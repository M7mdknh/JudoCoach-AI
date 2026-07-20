from fastapi.testclient import TestClient

import app.api.main as api_main
from app.api.main import app
from app.orchestrator import ResearchResult

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_research_rejects_too_short_question():
    response = client.post("/research", json={"question": "short"})

    assert response.status_code == 422


def test_research_returns_structured_response(monkeypatch):
    async def fake_run_research(question, approved_to_save=False):
        return ResearchResult(
            status="awaiting_approval",
            result="Draft findings about Judo grip strength.",
            report_id="abc123",
        )

    monkeypatch.setattr(api_main, "run_research", fake_run_research)

    response = client.post(
        "/research",
        json={
            "question": "How do I improve my grip strength for Judo?",
            "require_approval": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_approval"
    assert body["report_id"] == "abc123"


def test_research_handles_unexpected_error_without_leaking_details(monkeypatch):
    async def failing_run_research(question, approved_to_save=False):
        raise RuntimeError("some internal detail that should not leak")

    monkeypatch.setattr(api_main, "run_research", failing_run_research)

    response = client.post(
        "/research",
        json={"question": "How do I improve my grip strength for Judo?"},
    )

    assert response.status_code == 500
    assert "internal detail" not in response.json()["detail"]
