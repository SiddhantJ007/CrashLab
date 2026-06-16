# Build Notes

## Runtime
- Python 3.12+
- FastAPI application
- Render-hosted web service

## Dependencies
See `requirements.txt` for the exact pinned runtime set.

## Important Hosted Runtime Notes
- Render free can cold start after inactivity
- hosted persistence should use Supabase, not local SQLite writes
- provider credentials should be set via environment variables

## Local Build
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
