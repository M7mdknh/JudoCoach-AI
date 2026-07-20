# JudoCoach AI (EvidenceOps Agent)

A governed, evidence-grounded research agent built with LlamaIndex. It
answers Judo coaching questions from a private, indexed knowledge base,
uses a bounded set of tools, requires explicit human approval before
saving a report, and records every consequential action to an audit log.

This is the LlamaIndex Bootcamp "EvidenceOps Agent" project, adapted to a
Judo-coaching domain.

## Architecture

```
User / API Client
      |
      v
Input Validation (Pydantic)
      |
      v
LlamaIndex FunctionAgent
   |        |         |
   |        |         +--> record_audit_event --> reports/audit_log.jsonl
   |        +-------------> save_report (only present after approval)
   |                        --> reports/<slug>.md
   +----------------------> knowledge_base_search / compare_sources
                             |
                             v
                        VectorStoreIndex
                             |
                             v
                     data/*.md (Judo knowledge base)
```

The key governance property: **`save_report` does not exist in the
agent's tool list at all on an unapproved run** (see
`app/tools/research_tools.py::build_tools`). This is stronger than a
system-prompt instruction telling the model not to save — the model has
no capability to save until the caller explicitly sets
`approved_to_save=True`.

## Project Structure

```
app/
  agents/research_agent.py   FunctionAgent + system prompt
  api/main.py                FastAPI app (/health, /research)
  services/llm.py            Settings.llm / Settings.embed_model config
  services/index_service.py  Load persisted index -> query engine
  tools/research_tools.py    knowledge_base_search, compare_sources,
                              save_report, record_audit_event
  cli.py                     Interactive CLI
  config.py                  Pydantic-settings configuration
  ingest.py                  Chunking + metadata + index build/persist
  models.py                  API request/response schemas
  orchestrator.py            Approval threading, bounded execution, status
data/                        Judo knowledge base documents (Markdown)
storage/                     Persisted VectorStoreIndex artifacts
reports/                     Saved reports + audit_log.jsonl
tests/                       Unit and integration tests
scripts/evaluate.py          Evaluation harness (see below)
evaluation.jsonl             25-question evaluation dataset
evaluation_report.md         Generated evaluation results
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

`.env` is git-ignored (see `.gitignore`). Never commit a real API key.

## Build the Knowledge Base

```bash
python -m app.ingest
```

This chunks every file in `data/` with `SentenceSplitter(chunk_size=700,
chunk_overlap=100)`, tags each document with `source_type` and
`collection` metadata, embeds it, and persists the index to `storage/`.
It raises a clear `RuntimeError` if `data/` has no documents.

## Run the CLI

```bash
python -m app.cli
```

Ask a question, review the draft (and its `status`/`report_id`), then
choose whether to approve saving a final report.

## Run the API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"question": "What is O Soto Gari?", "require_approval": true}'
```

`question` must be 10–2000 characters (enforced by Pydantic); shorter or
longer requests are rejected with `422`.

## Testing

```bash
pytest -v
```

27 tests across configuration, ingestion, tools (including path-traversal
and empty-input rejection), the agent's tool-gated approval mechanism,
bounded execution, the API, and one adversarial prompt-injection test
(`tests/test_security.py`, using `data/adversarial_test.md`, which
contains a "SYSTEM OVERRIDE" instruction embedded in retrieved content).

## Evaluation

```bash
python -m scripts.evaluate
```

Runs every question in `evaluation.jsonl` (25 questions, including
approval-bypass attempts, a prompt-injection case, and two out-of-domain
questions) through the real agent, and regenerates
`evaluation_report.md` with measured retrieval hit rate, tool-selection
accuracy, approval compliance, loop detection, latency, and a narrative
failure analysis of real observed failures.

## Safety / Governance Controls

- **Tool-gated approval**: `save_report` is only added to the agent's
  tool list when `approved_to_save=True` (`app/tools/research_tools.py`,
  `app/agents/research_agent.py`, `app/orchestrator.py`).
- **Bounded execution**: `run_research` counts `ToolCallResult` events and
  cancels the run once `MAX_TOOL_CALLS` (default 8, configurable via
  `.env`) is exceeded, returning `status="failed"`.
- **Restricted file writes**: `save_report` sanitizes titles to
  alphanumeric/underscore characters only and writes exclusively under
  `config.reports_dir`, so a title cannot escape via path traversal.
- **Auditability**: every save/search action can be recorded via
  `record_audit_event`, correlated to a per-request `report_id`.
- **Prompt-injection resistance**: the system prompt explicitly instructs
  the model to treat retrieved document content as untrusted data, never
  as instructions — verified in `tests/test_security.py` against a
  document containing an embedded "SYSTEM OVERRIDE" string.

## Known Limitations

- Small, single-domain (Judo) knowledge base — 8 Markdown documents.
- No image/video understanding.
- Retrieval uses a single chunking configuration (700/100); no
  hybrid/keyword retrieval or reranking.
- The evaluation harness measures behavior against a small, hand-written
  25-question set — not a substitute for large-scale human evaluation.
- Bounded execution counts tool calls, not wall-clock time; a single slow
  tool call is not separately time-boxed.

## Ethical Considerations

- This assistant gives sport-coaching information, not medical advice;
  the `injuries.md` content is general safety guidance and should not
  replace consultation with a qualified professional.
- Retrieved content is treated as untrusted data specifically to reduce
  the risk of prompt injection from anything added to the knowledge base
  in the future.
- API keys and other secrets must never be committed; `.env` is
  git-ignored and `.env.example` ships with blank values only.
