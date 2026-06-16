# Target Integrations

CrashLab v1.1 currently supports Flowise and Dify as the two primary public target platforms.

## Flowise
### Use case
Flowise is used for orchestration-style or workflow-control targets.

### Runtime inputs
- base URL
- flow ID
- API key env var name
- timeout settings

### Current public family example
- `agent_orchestrator`

### What CrashLab captures
- response text
- execution IDs when exposed
- chat/session metadata when exposed
- flow-step summaries when exposed

## Dify
### Why Dify replaced Langflow in v1.1
Langflow was originally planned as the second platform, but hosted deployment required a separate Langflow server and ran into dependency, memory, port-binding, and runtime issues. Dify provided a faster hosted path for v1.1.

### Runtime inputs
- base URL
- endpoint path
- API key env var name
- optional output configuration fields

### Current public family example
- `rag_assistant`

### What CrashLab captures
- response text
- conversation/message/task metadata when exposed
- selected output metadata
- parse/schema validation status

## Custom API
CrashLab also includes a generic custom API path so compatible endpoints can be evaluated through the same family-based framework.

## Dynamic Targets
Targets can be:
- static bootstrap targets from `targets.json`
- dynamic targets created from the dashboard

Dynamic targets use a shared creation flow with platform-specific optional settings.
