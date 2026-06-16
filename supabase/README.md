# Supabase Setup

CrashLab v1.1 uses Supabase as its primary hosted persistence layer when configured.

## Tables
Default tables expected by the app:
- `crashlab_runs`
- `crashlab_cases`
- `crashlab_configured_targets`
- `crashlab_test_plans`
- `crashlab_target_probes`

## Schema File
Run the SQL in:
- `docs/supabase_schema.sql`

## Required Environment Variables
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_SCHEMA=public
```

## Important Security Note
Use the service-role key only on the server. Do not expose it in frontend JavaScript or public client-side config.
