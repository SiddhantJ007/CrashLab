# Supabase Migration

CrashLab originally used SQLite only.

## Why The Migration Was Needed
SQLite was fine for local development, but the public Render deployment needed durable shared state for:
- target onboarding
- run history
- compare results
- generated plans
- probe summaries

Render free does not provide dependable persistent local storage for this workflow, so SQLite alone was not sufficient in hosted mode.

## Migration Outcome
Supabase Postgres was added as the hosted primary persistence layer.

SQLite remains as a local fallback.

## Tables
Current default Supabase table names:
- `crashlab_runs`
- `crashlab_cases`
- `crashlab_configured_targets`
- `crashlab_test_plans`
- `crashlab_target_probes`

## Migration Steps
1. Create a Supabase project.
2. Open SQL Editor.
3. Run `docs/supabase_schema.sql`.
4. Add environment variables to Render.
5. Redeploy CrashLab.
6. Verify runs persist across restarts.

## Environment Variables
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_SCHEMA=public
```

## Security Note
Use the Supabase service-role key only in server-side runtime configuration. Never expose it in frontend code.
