# Architecture

CrashLab v1.1 is a single FastAPI application with a target-aware evaluation pipeline.

## High-Level Flow
1. Load bootstrap targets from `targets.json`.
2. Merge hosted or local configured targets from the persistence layer.
3. Resolve a suite source for the requested mode.
4. Execute cases through the appropriate platform adapter.
5. Parse outputs conservatively.
6. Run family-specific evaluation logic.
7. Aggregate weighted results.
8. Assign a trust label.
9. Persist the run and export evidence.

## Main Components
### FastAPI application
The web server exposes:
- dashboard UI
- target listing
- target onboarding/configuration
- run execution
- suite preview
- plan generation
- probe endpoint
- report export endpoints

### Adapter layer
Public v1.1 adapters:
- Flowise
- Dify
- Custom API

Adapter responsibilities:
- runtime URL construction
- request formatting
- timeout handling
- output extraction
- parse failure surfacing
- metadata capture

### Test-case layer
CrashLab stores reusable family templates and target-specific suites.

Inputs include:
- `case_id`
- `category`
- `prompt`
- `expected_behavior`
- `failure_conditions`
- `success_label`
- `failure_label`
- `risk_weight`

### Planner / intelligence layer
The planner can:
- use explicit target specs
- fall back to family templates
- generate target-specific plans with OpenAI if configured
- incorporate optional probe summaries

### Evaluator
The evaluator is family-aware.

Current families:
- `agent_orchestrator`
- `analysis_pipeline`
- `rag_assistant`
- `general_chatbot`
- `custom_or_unknown`

### Persistence
CrashLab now uses:
- Supabase first when configured
- SQLite fallback locally

Persisted entities:
- configured targets
- test plans
- probe summaries
- runs
- case results

## Why This Architecture
This structure keeps the core app reusable:
- adapters isolate platform-specific behavior
- family templates isolate evaluation intent
- the planner isolates test-plan generation
- the store layer isolates hosted vs local persistence
