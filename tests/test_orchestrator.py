import asyncio

import app.orchestrator as orch


class _DummyToolCallResult:
    pass


class _FakeHandler:
    def __init__(self, events, final_result="done"):
        self._events = events
        self._final_result = final_result
        self.cancelled = False

    async def stream_events(self):
        for event in self._events:
            yield event

    async def cancel_run(self):
        self.cancelled = True

    def __await__(self):
        async def _get():
            return self._final_result
        return _get().__await__()


class _FakeAgent:
    def __init__(self, handler):
        self._handler = handler

    def run(self, user_msg):
        return self._handler


def test_run_research_rejects_empty_question():
    result = asyncio.run(orch.run_research("   ", approved_to_save=False))

    assert result.status == "failed"
    assert result.report_id == ""


def test_run_research_stops_after_max_tool_calls(monkeypatch):
    monkeypatch.setattr(orch, "ToolCallResult", _DummyToolCallResult)
    monkeypatch.setattr(orch.config, "max_tool_calls", 3)

    events = [_DummyToolCallResult() for _ in range(10)]
    handler = _FakeHandler(events)

    monkeypatch.setattr(orch, "build_agent", lambda **kwargs: _FakeAgent(handler))

    result = asyncio.run(
        orch.run_research("Is grip strength important in Judo?", approved_to_save=False)
    )

    assert result.status == "failed"
    assert handler.cancelled is True
    assert "maximum" in result.result.lower()


def test_run_research_reports_awaiting_approval_status(monkeypatch):
    monkeypatch.setattr(orch, "ToolCallResult", _DummyToolCallResult)
    monkeypatch.setattr(orch.config, "max_tool_calls", 8)

    handler = _FakeHandler(events=[], final_result="draft findings")

    monkeypatch.setattr(orch, "build_agent", lambda **kwargs: _FakeAgent(handler))

    result = asyncio.run(
        orch.run_research("Is grip strength important in Judo?", approved_to_save=False)
    )

    assert result.status == "awaiting_approval"
    assert result.result == "draft findings"


def test_run_research_reports_approved_status(monkeypatch):
    monkeypatch.setattr(orch, "ToolCallResult", _DummyToolCallResult)
    monkeypatch.setattr(orch.config, "max_tool_calls", 8)

    handler = _FakeHandler(events=[], final_result="final report")

    monkeypatch.setattr(orch, "build_agent", lambda **kwargs: _FakeAgent(handler))

    result = asyncio.run(
        orch.run_research("Is grip strength important in Judo?", approved_to_save=True)
    )

    assert result.status == "approved"
