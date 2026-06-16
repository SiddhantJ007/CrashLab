# Security Policy

## Supported Scope
CrashLab v1.1 is a public MVP/demo. It is not a hardened multi-tenant production SaaS.

Security expectations for the current version:
- secrets should be stored in environment variables only
- dynamic target configuration is server-side
- the frontend must not receive provider API keys or Supabase service-role credentials
- hosted persistence should use server-side credentials only

## Sensitive Data
Do not commit:
- `.env`
- Flowise API keys
- Dify API keys
- OpenAI API keys
- Supabase service role keys
- private target URLs or internal endpoints unless intentionally public
- exported run files containing private data

## Security Risks To Be Aware Of
### Dynamic target URL risk
CrashLab allows runtime target configuration. That creates SSRF-style risk if arbitrary internal URLs are allowed. v1.1 should be treated as trusted-operator software, not open anonymous infrastructure.

Recommended future hardening:
- allowlist domains or protocols
- block private network ranges by default
- stricter URL validation and egress controls

### API key leakage
Provider credentials must remain server-side. Do not place Dify, Flowise, OpenAI, or Supabase service-role keys in frontend code.

### Shared run history
With Supabase-enabled persistence, run history becomes shared hosted application state. Multi-user separation and row-level security are not complete in v1.1.

### Prompt and output handling
Targets may process user-entered prompts and external workflow responses. Avoid using CrashLab with sensitive production data unless you have reviewed target-side data handling.

## Reporting a Security Issue
This repo is currently maintained as a portfolio/demo project.

For now:
- do not disclose private secrets in issues
- report concerns privately to the repository owner
- include reproduction steps, environment details, and the affected surface

## Recommended Deployment Hygiene
- use environment variables for all secrets
- rotate keys before public demos if they were previously exposed locally
- use Supabase service-role keys only on the server
- consider read-only public demos without arbitrary user target configuration if exposing broadly
