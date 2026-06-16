# CI/CD

CrashLab v1.1 includes lightweight CI expectations suitable for an MVP.

## Current Goal
Ensure the public repo stays in a working state before deployment.

## Recommended Pipeline
- install dependencies
- run compile check
- run pytest

## Typical Commands
```bash
python3 -m compileall app
./.venv/bin/python -m pytest -q
```

## Deployment Model
The current deployment model is straightforward:
- push to GitHub
- Render redeploys the FastAPI app
- runtime env vars are supplied through Render
- Supabase provides persistent hosted storage

## Future Improvements
- stronger linting
- staged deployment checks
- integration tests against non-production targets
- migration automation for persistence schema changes
