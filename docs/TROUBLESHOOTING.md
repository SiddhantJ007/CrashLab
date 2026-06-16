# Troubleshooting

## Dashboard shows missing config
Check that the required environment variables are set:
- Flowise: base URL, flow ID, API key
- Dify: base URL, API key
- Supabase: URL and service-role key if hosted persistence is expected

## Runs disappear after restart
If Supabase is not configured, CrashLab is likely using SQLite fallback only. On Render free, local filesystem persistence is not dependable for shared hosted history.

## Compare panel is empty
Possible causes:
- no recent runs exist yet
- runs failed before evaluation
- no evaluated failures exist in the latest visible runs
- persistence is not configured as expected

## Parse failed
The target responded, but CrashLab could not extract or validate the output using the expected parser/schema path.

## Execution unstable
The target timed out or failed upstream before all cases completed.

## Dify score is lower than expected
Common causes:
- answers without context instead of refusing
- ignores conflicting evidence
- weak evidence handling is too confident
- output format does not match the target family assumptions

## Flowise score is lower than expected
Common causes:
- unsafe shortcut approval
- poor ambiguity handling
- loop or max-iteration outputs
- workflow drifts into generic chat behavior
