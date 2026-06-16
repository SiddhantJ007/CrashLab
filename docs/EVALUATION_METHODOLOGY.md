# Evaluation Methodology

CrashLab evaluates observable behavior, not hidden internal reasoning.

## Case Execution
For each selected case, CrashLab:
1. sends the prompt to the configured target
2. captures response text and metadata
3. parses the output conservatively
4. routes the case to a family-specific evaluator
5. records case-level status and notes

## Case Statuses
- `evaluated`
- `execution_failed`
- `response_parse_failed`
- `timeout`
- `empty_response`
- `skipped`

## Weighted Scoring
CrashLab uses weighted case scoring so higher-risk failures matter more than cosmetic misses.

A conceptual form is:

`Score = weighted passed or partial-credit outcomes / weighted total`

## Trust Labeling Philosophy
CrashLab does not treat parse failures or execution failures as ordinary benchmark scores.

Examples:
- a run that times out is not trustworthy just because some cases passed
- a run that returns malformed output is not comparable to a clean evaluated run
- a run that completes but fails critical safety checks should not be presented as simply “good but imperfect”

## Why Family Awareness Matters
A workflow orchestrator should not be judged like a retrieval assistant, and a schema-driven analysis pipeline should not be judged like open-ended chat. Family-specific evaluation makes the results more defensible.
