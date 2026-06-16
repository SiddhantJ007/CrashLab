# Database and Persistence

CrashLab has two persistence modes.

## 1. SQLite fallback
SQLite is used for:
- local development
- lightweight local testing
- offline or simple single-user runs

Pros:
- zero setup
- simple local iteration

Limitations:
- not reliable for hosted shared persistence on Render free
- local filesystem writes can disappear across restarts/redeploys

## 2. Supabase primary hosted persistence
Supabase Postgres is now the preferred hosted persistence layer.

It stores:
- configured targets
- test plans
- probe summaries
- runs
- case results

Pros:
- shared across users
- survives restarts and redeploys
- works well with Render-hosted FastAPI

## Persistence Behavior in v1.1
CrashLab checks for Supabase config first. If available, it reads/writes there. Otherwise, it falls back to SQLite.

## Shared Visibility
With Supabase enabled:
- users see the same hosted run history
- compare views and recent runs survive Render cold starts
- generated plans and dynamic targets persist beyond one app instance
