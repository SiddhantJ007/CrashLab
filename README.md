# CrashLab v1

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-app-009688?logo=fastapi&logoColor=white)
![Render Ready](https://img.shields.io/badge/Render-ready-46E3B7?logo=render&logoColor=111111)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-compile%20%2B%20tests-2088FF?logo=githubactions&logoColor=white)

LLM workflow reliability lab for testing Flowise, Langflow, and custom API agents across failure families like prompt injection, hallucination, schema drift, parse failures, and unstable execution.

CrashLab is a target-aware evaluation platform for API-accessible LLM workflows. It runs structured test suites against configured Flowise, Langflow, and compatible custom API targets, then turns observable behavior into trust labels, weighted scores, and exportable reports.

This public v1 release is intentionally small and safe to ship:
- one FastAPI app
- no bundled Flowise or Langflow server
- no WebArena in the public UI
- no private endpoints, API keys, or local databases committed
- a self-contained sample mode so the dashboard is still meaningful on a fresh deploy

## Live Demo
- Live Demo: coming after Render deployment
- GitHub Actions: compile check + pytest suite via `.github/workflows/ci.yml`

## Problem It Solves
LLM workflows are easy to demo and hard to evaluate repeatably. A few manual prompts do not reveal whether a target:
- follows the expected output schema
- resists prompt injection or unsafe shortcuts
- stays grounded in source evidence
- fails cleanly when parsing or execution breaks
- produces results that are trustworthy enough to compare over time

CrashLab addresses that by making the evaluation target-aware instead of treating every workflow like a generic chatbot.

## What CrashLab v1 Does
CrashLab v1 supports:
- target onboarding from the dashboard
- adapter-based execution for Flowise, Langflow, and Custom API targets
- family-based suite selection for `agent_orchestrator`, `analysis_pipeline`, `rag_assistant`, `general_chatbot`, and `custom_or_unknown`
- explicit target specs when a target needs a more specific suite than the family default
- generated or adapted test plans stored in SQLite
- optional probe-assisted profiling for a lightweight output-shape check
- weighted scoring and conservative trust labels
- Markdown, JSON, and CSV exports
- a public-safe sample history mode for recruiter demos

## Recruiter Demo Script
1. Open the dashboard.
2. View the sample Flowise and Langflow targets.
3. Preview a family-specific suite from a target card.
4. Inspect the sample run history.
5. Open a run and review the trust label and weighted score.
6. Export the Markdown, JSON, or CSV report.
7. Add a live Flowise, Langflow, or Custom API target from the dashboard for real external evaluation.

## Demo Mode vs Live Target Mode
### Demo mode
- uses seeded sanitized historical runs
- works on a fresh deploy without any external workflow configured
- demonstrates target cards, suite preview, trust labels, weighted scoring, run history, and exports

### Live target mode
- requires a user-provided endpoint or flow ID
- requires any needed API key environment variable to be configured by the user
- runs real external evaluations through the adapter layer

CrashLab does not fabricate fresh live evaluations when no real external target is configured.

## Supported Adapters
CrashLab v1 currently exposes these adapters in the public product flow:
- `Flowise`
- `Langflow`
- `Custom API`

WebArena code may remain in the repository for private experiments, but it is hidden from the public UI and not part of the shipped v1 workflow.

## Supported Evaluation Families
### `agent_orchestrator`
Used for supervisor or routing workflows.

Typical checks:
- relevant routing
- code-review workflow structure
- ambiguity handling
- unsafe shortcut resistance
- conflicting evidence handling
- loop safety

### `analysis_pipeline`
Used for structured analysis workflows such as feedback analysis.

Typical checks:
- schema correctness
- sentiment and summary quality
- weak-evidence handling
- injection resistance
- grounded recommendations

### `rag_assistant`
Used for retrieval-grounded assistants.

Typical checks:
- grounded answer behavior
- no-context refusal
- retrieved-text injection resistance
- conflicting context handling
- context-boundary behavior

### `general_chatbot`
Used for generic assistant-style targets.

Typical checks:
- instruction following
- off-scope handling
- hallucination risk
- format consistency
- refusal behavior

### `custom_or_unknown`
Used when a workflow does not fit the families above. CrashLab blocks evaluation until a reviewed plan exists.

## Architecture Overview
The evaluation pipeline is:

1. Configure or load a target
2. Resolve the suite source
   - approved generated plan
   - explicit target spec
   - default family template
   - block `custom_or_unknown` without a plan
3. Execute each case through the target adapter
4. Parse the observable response conservatively
5. Route the case through a family-aware evaluator
6. Aggregate weighted results into a run score
7. Assign a trust label
8. Export Markdown, JSON, or CSV evidence

A concise architecture note is also available in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## How Evaluations Work
Each case includes:
- `case_id`
- `category`
- `prompt`
- `expected_behavior`
- `failure_conditions`
- `success_label`
- `failure_label`
- `risk_weight`

CrashLab sends the prompt to the real target API, captures observable output and metadata, then evaluates the case using logic appropriate to the selected family.

Two design choices matter:
- parse failures and execution failures are not converted into normal benchmark scores
- trusted comparison only uses runs with complete usable evaluated output

## Trust Labels
CrashLab uses conservative trust labels:
- `Trusted`: all required cases produced usable evaluated output and no critical safety failure occurred
- `Needs Review`: the run completed but output quality was mixed
- `Parse Failed`: the target responded but the output did not match the expected parse or schema path
- `Execution Failed`: the workflow or upstream provider failed before evaluation completed
- `Execution Unstable`: timeouts or partial execution prevented a complete run
- `Unsafe / Ungrounded`: the run completed but failed a critical safety or grounding check

## Reports and Outputs
CrashLab can export:
- Markdown summary
- JSON run payload
- CSV case table

The exports include:
- target metadata
- suite source
- trust label
- weighted score when trustworthy
- case-level results
- selected execution metadata
- recommended fixes derived from failure categories

## Public Safety
- no API keys are included in the repo
- no WebArena dataset or environment is part of the public product flow
- no private live target configuration is bundled in `targets.json`
- local databases, reports, generated exports, screenshots, and virtual environments are ignored via `.gitignore`

## Demo Modes in This Public Release
### Self-contained sample mode
A fresh public deployment seeds sanitized historical sample runs for the built-in Flowise and Langflow example targets.

This gives you:
- target cards
- suite preview
- run history
- trust labels
- weighted scores
- export buttons

These sample runs are clearly historical demo evidence, not fresh live evaluations.

### Optional live external target mode
To run a fresh evaluation, add or edit a target in the dashboard and provide a real external endpoint.

CrashLab v1 does not bundle or deploy:
- Flowise itself
- Langflow itself
- WebArena

Those systems should be treated as optional external targets.

## Local Run
Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start CrashLab:

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Render Deployment
CrashLab v1 is designed to run as a single FastAPI app on Render.

### Start command
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Recommended environment variables
Use placeholder values only until you intentionally connect live targets:

```bash
FLOWISE_API_KEY=your_flowise_key_here
LANGFLOW_API_KEY=your_langflow_key_here
OPENAI_API_KEY=optional_for_planner
CRASHLAB_LOAD_DOTENV=0
CRASHLAB_SEED_SAMPLE_DATA=1
CRASHLAB_DB_PATH=app/data/crashlab.db
```

### Persistent vs ephemeral storage
Ephemeral mode:
- simplest option for a recruiter demo
- sample runs are reseeded on each cold deploy if the DB is empty

Persistent disk mode:
- recommended if you want onboarded targets and run history to survive restarts
- point `CRASHLAB_DB_PATH` at the mounted disk path

## Public-Safe Bootstrap Config
- `targets.json` ships with sanitized example targets and no live private endpoints
- `targets.example.json` shows the fake values expected for Flowise and Langflow
- real target credentials should be provided through environment variables and the dashboard, not committed to git

## Testing
Run the local checks:

```bash
python -m compileall app
./.venv/bin/python -m pytest -q
```

The included test suite covers:
- suite resolution priority
- evaluator trust-label edge cases
- adapter parsing fixtures
- FastAPI smoke routes

## Tech Stack
- FastAPI
- Jinja2 templates
- vanilla JavaScript
- SQLite
- httpx
- Pydantic
- pytest
- GitHub Actions

## What This Project Proves
CrashLab is intended to show practical AI reliability thinking, not just prompt demos. The repo demonstrates:
- adapter-based integration with LLM workflow platforms
- repeatable evaluation datasets for AI workflows
- failure analysis for parse, schema, grounding, and safety issues
- conservative reporting that refuses to overclaim trust
- product thinking around onboarding, reporting, and demo-safe deployment

## Limitations
CrashLab v1 does not claim universal testing for arbitrary public agents.

Current limits:
- evaluation quality depends on the selected target family and expected output style
- black-box and gray-box only unless the target exposes richer metadata
- generated test plans still benefit from human review
- built-in evaluators are strongest for the currently exercised Flowise and Langflow patterns
- live external targets are optional and must be configured separately

## v2 Roadmap
Intentionally deferred from this public v1 release:
- deeper graph introspection for Flowise and Langflow
- stronger plan generation and review workflows
- target edit/delete management polish
- richer regression tracking across workflow versions
- CI-triggered recurring evaluation jobs
- broader adapter coverage

## What I Learned
Building CrashLab changed the framing from “can this workflow answer a prompt?” to “can this workflow be trusted for its intended job?” The most important outcome was not a single score, but a reliable distinction between:
- valid evaluated output
- parse or schema failures
- execution failures
- unsafe but fluent responses

That distinction is what makes the reports defensible.
