# Test Case Families

CrashLab uses family-specific suites instead of one universal chatbot benchmark.

## agent_orchestrator
Used for routing and supervisor-style workflows.

Typical categories:
- relevant routing
- code-review workflow structure
- ambiguity handling
- unsafe shortcut resistance
- conflicting evidence handling
- loop safety

## analysis_pipeline
Used for structured analysis tasks.

Typical categories:
- schema correctness
- negative or mixed signal detection
- weak evidence handling
- injection resistance
- grounded recommendation quality

## rag_assistant
Used for retrieval-grounded assistants.

Typical categories:
- grounded context answer
- no-context refusal
- retrieved-text injection resistance
- conflicting context handling
- citation behavior
- hallucination beyond context

## general_chatbot
Used for generic assistant-style workflows.

Typical categories:
- instruction following
- off-scope handling
- hallucination risk
- format consistency
- guardrail/refusal behavior

## custom_or_unknown
Used when a target does not clearly fit a supported family.

Behavior:
- block execution until a reviewed plan exists

## Case Attributes
Each case can include:
- `case_id`
- `category`
- `prompt`
- `expected_behavior`
- `failure_conditions`
- `success_label`
- `failure_label`
- `risk_weight`
- `evaluator_hints`
