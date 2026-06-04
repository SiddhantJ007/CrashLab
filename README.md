# CrashLab

CrashLab is a target-aware evaluation platform for **API-accessible LLM workflows**.

Instead of treating every system like a generic chatbot, CrashLab evaluates workflows according to what they are supposed to do: orchestration, structured analysis, retrieval-grounded answering, or general assistant behavior. It runs real API calls, parses outputs conservatively, detects failure modes such as schema drift or unsafe responses, and produces repeatable reports in Markdown, JSON, and CSV.

## The Problem It Solves
LLM workflows are easy to demo and hard to evaluate well.

In practice, teams often rely on manual prompt testing, screenshot-based validation, or ad hoc spot checks. That breaks down when a workflow has:
- routing or orchestration logic
- multiple output stages
- strict JSON or schema expectations
- safety constraints
- grounding requirements
- unstable execution paths such as timeouts or provider failures

CrashLab is built to make those behaviors **repeatable, inspectable, and comparable** without pretending every LLM application should be judged by the same rubric.

## What This Project Demonstrates
This project is meant to show practical AI reliability engineering skills beyond prompt demos:
- family-specific evaluation instead of one-size-fits-all prompt checks
- failure analysis for parse, execution, grounding, and safety problems
- structured output validation and schema-aware scoring
- repeatable local evaluation runs with stored case results
- target onboarding for new API-accessible workflows
- exportable reporting for debugging and documentation

## Key Features
- **Target onboarding UI** for Flowise, Langflow, and Custom API-style targets
- **Family-based suites** for different workflow behaviors
- **Platform adapters** for real API execution and response normalization
- **Generated/adapted test plans** with fallback behavior
- **Optional probe-assisted profiling** for lightweight output-shape inspection
- **Conservative parsing** that refuses to score unusable outputs as valid results
- **Trust labels** that separate real quality issues from execution or parse failures
- **Exportable reports** in Markdown, JSON, and CSV
- **Stored run history** and case-level evidence in SQLite

## Tech Stack
- **Backend:** Python, FastAPI
- **HTTP client:** `httpx`
- **Templating/UI:** Jinja2, vanilla JavaScript, CSS
- **Persistence:** SQLite
- **Document/report generation:** Markdown, JSON, CSV, Word export support in the project workflow
- **Workflow targets:** Flowise, Langflow, Custom API-style integrations

## Architecture Overview
At a high level, CrashLab works like this:

1. A target is loaded from `targets.json` or onboarded from the UI.
2. The target is assigned a family such as `agent_orchestrator` or `analysis_pipeline`.
3. CrashLab resolves the evaluation suite using this priority:
   1. approved generated plan
   2. explicit target spec
   3. default family template
   4. block unsupported `custom_or_unknown` targets without a reviewed plan
4. The relevant adapter calls the real target API.
5. CrashLab parses the returned output conservatively.
6. A family-specific evaluator scores the response and records failure details.
7. The runner assigns a trust label.
8. Results are stored and can be exported as Markdown, JSON, or CSV.

For a more technical walkthrough, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Supported Target Types
Visible and implemented target paths in the codebase include:
- **Flowise**
  - intended for orchestration-style or routing workflows
- **Langflow**
  - intended for structured analysis pipelines and multi-output flows
- **Custom API**
  - bounded generic adapter for API-accessible targets with simpler text-style execution

Target families currently supported in the evaluation layer:
- `agent_orchestrator`
- `analysis_pipeline`
- `rag_assistant`
- `general_chatbot`
- `custom_or_unknown`

## How Evaluations Work
CrashLab uses **case-based evaluation**.

Each case includes fields such as:
- `case_id`
- `category`
- `prompt`
- `expected_behavior`
- `failure_conditions`
- `success_label`
- `failure_label`
- `risk_weight`

Those cases act as a lightweight evaluation dataset. They can come from:
- a built-in family template
- an explicit target spec
- a generated or adapted test plan

Each run records:
- execution outcome
- parsed response text
- evaluator notes
- case-level pass/fail or partial quality
- runtime metadata such as suite source, target source, flow ID, base URL, and selected output path when relevant

## Example Failure Categories
CrashLab is designed to surface workflow-specific reliability issues such as:
- hallucination risk
- prompt injection or instruction override
- schema mismatch
- response parse failure
- empty response
- unsafe shortcut approval
- weak evidence overconfidence
- ungrounded recommendation
- timeout or execution instability
- provider quota / upstream API failure

## Trust Labels
CrashLab does not treat every completed HTTP call as a valid benchmark result.

It uses these trust labels:
- **Trusted**
- **Needs Review**
- **Parse Failed**
- **Execution Failed**
- **Execution Unstable**
- **Unsafe / Ungrounded**

This is one of the main design choices in the project: if parsing fails or execution is unstable, CrashLab surfaces that directly instead of showing a misleading benchmark-style score.

## Report Outputs
CrashLab supports multiple export formats for completed runs:
- **Markdown**
- **JSON**
- **CSV**

These reports can include:
- target metadata
- family and suite source
- trust label
- score summary
- case-level outcomes
- selected runtime metadata such as flow ID or output-path details
- recommended fixes derived from failed categories

## Running Locally
1. Create and activate a Python virtual environment.
2. Install dependencies.
3. Add environment variables.
4. Start the app.

Example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

## Environment Variables
Use placeholder values only. Do **not** commit real secrets.

Typical environment variables include:

```bash
FLOWISE_API_KEY=your_flowise_api_key
LANGFLOW_API_KEY=your_langflow_api_key
OPENAI_API_KEY=optional_planner_key
OPENAI_PLANNER_MODEL=optional_model_name
```

Depending on the target you onboard, you may also configure different API key environment variable names through the UI.

## Current Integrations Visible in the Code
Based on the repository code paths:
- Flowise adapter for Prediction API execution
- Langflow adapter for flow execution and output selection
- Custom API adapter for bounded generic target execution
- SQLite-backed storage for runs, configured targets, test plans, and probe summaries
- planner module for generated/adapted plans
- runner module for execution, trust labels, scoring, and export generation

## What I Learned
This project pushed me beyond prompt engineering into **evaluation system design** for AI workflows.

The biggest lessons were:
- evaluation must match the target's actual role, not just its model output style
- structured output parsing is often as important as prompt quality
- execution failure and parse failure must be kept separate from model-quality scoring
- AI reliability tooling benefits from conservative defaults more than optimistic dashboards
- a useful AI tool is not just a model wrapper; it needs evidence, failure reporting, and repeatable workflows

## Future Improvements
- richer graph-level metadata ingestion from Flowise and Langflow
- explicit plan review and editing in the UI
- stronger Custom API schema configuration
- regression testing across workflow versions
- CI integration for repeatable evaluation runs
- better longitudinal reporting and trend comparison
- edit/delete management for onboarded targets

## Notes for a Public Repo
This repository should **not** include:
- `.env` files
- real API keys or tokens
- local databases with private test results unless intentionally sanitized
- local machine paths in docs or screenshots
- virtual environments, caches, or generated report folders

If you make this repository public, review tracked files carefully before pushing.
