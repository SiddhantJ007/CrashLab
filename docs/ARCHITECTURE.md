# CrashLab Architecture

CrashLab is a single FastAPI application that evaluates API-accessible LLM workflows through a target-aware pipeline.

## Evaluation Flow
1. Load sanitized bootstrap targets from `targets.json`.
2. Merge dashboard-created targets from SQLite.
3. Resolve the active suite source for the selected mode.
   - approved generated plan
   - explicit target spec
   - default family template
   - block `custom_or_unknown` without a reviewed plan
4. Execute each case through the platform adapter.
5. Parse output conservatively.
6. Route the case through a family-aware evaluator.
7. Aggregate weighted results.
8. Assign a trust label.
9. Export Markdown, JSON, or CSV.

## Adapters
CrashLab v1 exposes these public adapters:
- Flowise
- Langflow
- Custom API

Each adapter is responsible for:
- runtime request formatting
- endpoint execution
- response parsing
- metadata capture
- explicit parse failure reporting when output is unusable

## Families
The family system keeps evaluation tied to the target’s intended job:
- `agent_orchestrator`
- `analysis_pipeline`
- `rag_assistant`
- `general_chatbot`
- `custom_or_unknown`

This prevents a workflow orchestrator from being graded like a generic chatbot, or a schema-driven analysis pipeline from being treated like open-ended chat.

## Trust Model
CrashLab does not turn every run into a benchmark score.

Execution failures, timeouts, and parse failures are surfaced as trust issues instead of being hidden behind a normal-looking score. Trusted comparison only includes complete runs with usable evaluated output.

## Public Demo Mode
The public v1 release seeds sanitized historical sample runs when the local database is empty. This keeps the Render demo useful without bundling private endpoints, local databases, or deployed Flowise/Langflow instances.

Sample mode demonstrates:
- target cards
- suite preview
- run history
- weighted scoring
- trust labels
- report export

Fresh live runs still require a user-configured external target.
