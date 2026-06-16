# Testing

CrashLab includes lightweight automated checks for the v1.1 MVP.

## Current Test Coverage
- adapter parsing behavior
- evaluator logic
- trust-label edge cases
- API smoke endpoints
- suite resolution behavior

## Main Commands
Compile check:
```bash
python3 -m compileall app
```

Pytest suite:
```bash
./.venv/bin/python -m pytest -q
```

## What The Tests Are For
The tests are meant to protect:
- response parsing behavior
- score/trust regressions
- endpoint behavior
- public target visibility assumptions

## What The Tests Are Not
The current suite is not a full enterprise test harness. It does not replace:
- large-scale load testing
- security auditing
- end-to-end hosted integration validation against every provider state
