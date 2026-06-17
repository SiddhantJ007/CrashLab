# CrashLab v1.1

LLM workflow evaluation platform for testing Flowise, Dify, and compatible API-accessible AI agents across failure families such as unsafe shortcuts, hallucination risk, prompt injection, parse failures, schema drift, weak evidence handling, and execution instability.

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-app-009688?logo=fastapi&logoColor=white)
![Render Ready](https://img.shields.io/badge/Render-ready-46E3B7?logo=render&logoColor=111111)
![Supabase](https://img.shields.io/badge/Supabase-persistence-3ECF8E?logo=supabase&logoColor=white)

CrashLab is a target-aware evaluation lab for API-accessible LLM workflows. It executes structured test suites against configured targets, scores observable behavior, assigns conservative trust labels, and exports evidence in Markdown, JSON, and CSV.

This is a working MVP and recruiter-facing demo, not a full enterprise platform.

## Live Demo
- Live demo: [CrashLab on Render](https://crashlab.onrender.com)
- Video walkthrough: 

[![CrashLab Loom Demo](docs/assets/loom-preview.png)](https://www.loom.com/share/1a6fc484dc93431f801e0e6d47d5a446)

### Screenshots
<table>
  <tr>
    <td width="50%" align="center">
      <a href="docs/assets/suite-preview.png"><img src="docs/assets/suite-preview.png" alt="CrashLab suite preview" width="100%"/></a><br/>
      <strong>Suite Preview</strong>
    </td>
    <td width="50%" align="center">
      <a href="docs/assets/custom-target.png"><img src="docs/assets/custom-target.png" alt="CrashLab add target form" width="100%"/></a><br/>
      <strong>Add Target</strong>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <a href="docs/assets/live-run.png"><img src="docs/assets/live-run.png" alt="CrashLab live run log" width="100%"/></a><br/>
      <strong>Live Run</strong>
    </td>
    <td width="50%" align="center">
      <a href="docs/assets/report-export.png"><img src="docs/assets/report-export.png" alt="CrashLab export and recent runs" width="100%"/></a><br/>
      <strong>Report Export</strong>
    </td>
  </tr>
</table>

The Loom preview above already covers the main dashboard view, so the supporting screenshots focus on suite preview, target onboarding, live execution, and export evidence without repeating the same hero view.

## What Problem It Solves
LLM workflows are easy to demo and difficult to test repeatably. A handful of manual prompts does not reliably answer:
- Does the workflow stay within its intended scope?
- Does it resist prompt injection or unsafe user overrides?
- Does it remain grounded in the provided evidence or context?
- Does it fail clearly when parsing or execution breaks?
- Can two targets be compared using the same family-appropriate evaluation standard?

CrashLab addresses that by making evaluation target-aware rather than treating every workflow like a generic chatbot.

## Current Scope
CrashLab v1.1 currently supports:
- Flowise targets
- Dify targets
- Custom API targets through the shared adapter path
- Static bootstrap targets from `targets.json`
- Dynamic targets added from the dashboard
- Family-based test suite selection
- Optional OpenAI-assisted target analysis and test-plan generation
- Optional probe-assisted target profiling
- Supabase-backed hosted persistence
- SQLite local fallback for development
- Markdown, JSON, and CSV report export

## Supported Target Families
- `agent_orchestrator`
- `analysis_pipeline`
- `rag_assistant`
- `general_chatbot`
- `custom_or_unknown`

## Supported Integrations
### Flowise
Used for orchestration-style or workflow-control targets.

### Dify
Used as the second hosted v1.1 platform after Langflow was deferred for deployment/runtime reasons.

### Custom API
Allows evaluation of compatible API-accessible workflows using the same general target model.

## How CrashLab Works
1. Load bootstrap targets from `targets.json`.
2. Merge dynamic targets from persisted storage.
3. Resolve a suite source in this priority order:
   - approved generated plan
   - explicit target spec
   - default family template
   - block `custom_or_unknown` without a reviewed plan
4. Execute each case against the real target adapter.
5. Parse the response conservatively.
6. Evaluate the result using family-specific logic.
7. Aggregate weighted case scores.
8. Assign a trust label.
9. Store the run and export evidence.

## Trust Labels
CrashLab uses conservative labels instead of forcing every run into a benchmark number:
- `Trusted`
- `Needs Review`
- `Parse Failed`
- `Execution Failed`
- `Execution Unstable`
- `Unsafe / Ungrounded`

## Persistence Model
CrashLab started with SQLite as a lightweight MVP store.

That worked locally, but it was not reliable for hosted persistence on Render free because local filesystem writes are not durable across restarts/cold starts. To solve that, v1.1 adds Supabase Postgres as the primary hosted persistence layer.

Current persistence behavior:
- Supabase first when configured
- SQLite fallback for local development and simple local testing

## Deployment Summary
### Why not Vercel?
Vercel’s serverless filesystem model is a poor fit for writable local SQLite persistence.

### Why Render?
Render was a better fit for a single FastAPI app deployment, but Render free still does not provide dependable persistent local storage for this use case.

### Why Supabase?
Supabase provides a low-friction hosted Postgres backend that preserves:
- targets
- runs
- case results
- generated plans
- probe summaries

## Environment Variables
Use environment variables only. Do not hardcode API keys in client-side code.

Required or commonly used variables:
```env
FLOWISE_API_KEY=...
FLOWISE_BASE_URL=...
FLOWISE_FLOW_ID=...

DIFY_API_KEY=...
DIFY_BASE_URL=https://api.dify.ai/v1

OPENAI_API_KEY=optional_for_target_analysis_layer

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_SCHEMA=public

CRASHLAB_DB_PATH=app/data/crashlab.db
CRASHLAB_LOAD_DOTENV=1
CRASHLAB_SEED_SAMPLE_DATA=0
```

See `.env.sample` for placeholders.

## Local Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Testing
```bash
python3 -m compileall app
./.venv/bin/python -m pytest -q
```

## Key Engineering Decisions
- FastAPI monolith instead of split frontend/backend for v1 speed
- Target-family evaluation instead of one generic scoring rubric
- Conservative trust labels instead of misleading scores on parse/execution failure
- Render deployment for the web app
- Supabase persistence for hosted state
- Langflow deferred; Dify selected as the second platform for v1.1

## Security Notes
- Keep Flowise, Dify, OpenAI, and Supabase credentials server-side only.
- Do not expose service role keys in client-side JavaScript.
- Dynamic target URLs introduce SSRF-style risk if not constrained.
- Multi-user auth and row-level security are future improvements, not completed v1.1 features.

## What This Project Demonstrates
CrashLab is meant to show:
- structured AI evaluation thinking
- adapter-based integration design
- platform deployment tradeoff analysis
- hosted persistence migration under real constraints
- pragmatic productization of LLM reliability tooling

## Documentation Index
- [docs/VISION.md](docs/VISION.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/TARGET_INTEGRATIONS.md](docs/TARGET_INTEGRATIONS.md)
- [docs/INTELLIGENCE_LAYER.md](docs/INTELLIGENCE_LAYER.md)
- [docs/TEST_CASE_FAMILIES.md](docs/TEST_CASE_FAMILIES.md)
- [docs/EVALUATION_METHODOLOGY.md](docs/EVALUATION_METHODOLOGY.md)
- [docs/DATABASE_PERSISTENCE.md](docs/DATABASE_PERSISTENCE.md)
- [docs/SUPABASE_MIGRATION.md](docs/SUPABASE_MIGRATION.md)
- [docs/TESTING.md](docs/TESTING.md)
- [docs/CI_CD.md](docs/CI_CD.md)
- [docs/ENGINEERING_DECISIONS.md](docs/ENGINEERING_DECISIONS.md)
- [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md)
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/LIMITATIONS.md](docs/LIMITATIONS.md)
- [CHANGELOG.md](CHANGELOG.md)

## What I Learned
- deployment constraints shape product architecture as much as model behavior does
- persistence choices matter early for any evaluation product with shared run history
- family-aware evaluation is much more defensible than generic chatbot scoring
- conservative trust labeling is better than presenting false precision

## Future Improvements
- multi-user auth and row-level access controls
- stronger SSRF protections around dynamic targets
- richer Dify and Flowise metadata ingestion
- Langflow reintroduction if hosted deployment becomes practical
- additional platforms beyond Flowise and Dify
- CI-driven regression runs across target versions
