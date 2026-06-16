# Deployment

CrashLab v1.1 is deployed as a single FastAPI web app on Render.

## Why Render
CrashLab needs:
- a long-running Python web service
- server-side secret handling
- a simpler deployment model than serverless-only platforms

Render was chosen because it fits a single FastAPI app well.

## Why Not Vercel
The project originally used SQLite for persistence. Vercel’s serverless runtime is not a good fit for writable local SQLite state because local writes are not durable in the way the app needs.

## Render Constraint
Render free web services can spin down and do not provide dependable persistent local filesystem behavior for this use case.

That made local SQLite insufficient for hosted shared history.

## v1.1 Solution
Hosted persistence was moved to Supabase Postgres.

Current persistence order:
1. Supabase when configured
2. SQLite fallback for local development

## Render Setup
### Build command
```bash
pip install -r requirements.txt
```

### Start command
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Required Render Environment Variables
```env
FLOWISE_API_KEY=...
FLOWISE_BASE_URL=...
FLOWISE_FLOW_ID=...
DIFY_API_KEY=...
DIFY_BASE_URL=https://api.dify.ai/v1
OPENAI_API_KEY=optional
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_SCHEMA=public
CRASHLAB_LOAD_DOTENV=0
CRASHLAB_SEED_SAMPLE_DATA=0
```

## Post-Deploy Checklist
- confirm `/health` works
- confirm targets load
- confirm a Flowise run persists
- confirm a Dify run persists
- confirm recent runs survive a restart/redeploy
