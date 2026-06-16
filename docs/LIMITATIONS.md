# Limitations

CrashLab v1.1 is a working MVP, not a complete production evaluation platform.

## Current Limitations
- evaluates observable API behavior only
- does not guarantee visibility into hidden internal tool calls or reasoning
- family selection still matters; wrong family choice weakens result quality
- generated test plans are assistive and still need human judgment
- multi-user auth and row-level access controls are not complete
- dynamic target URLs introduce future security-hardening needs
- current hosted integrations are intentionally limited to keep the public demo small and stable

## Hosted Demo Constraints
- Render free can cold start
- live target quality still depends on the configured external workflow
- provider quotas and rate limits can affect run stability

## Langflow Status
Langflow is not part of the shipped public v1.1 integration set. It was deferred due to deployment/runtime complexity in the hosted environment.
