# CrashLab Architecture

CrashLab evaluates **API-accessible LLM workflows** through a target-aware pipeline.

## Evaluation Pipeline

1. **Test case selection**
   - CrashLab resolves a suite from one of three sources:
     1. approved generated plan
     2. explicit target spec
     3. default family template
   - `custom_or_unknown` targets are blocked unless a reviewed plan exists.

2. **Target execution**
   - The runner sends each case prompt through a platform adapter.
   - Current adapters include Flowise, Langflow, and a bounded Custom API path.

3. **Response parsing**
   - CrashLab extracts the most trustworthy output candidate it can find.
   - Parsing is conservative by design.
   - If a response cannot be parsed into a stable text or schema-shaped output, the case is not treated as a valid benchmark success.

4. **Failure detection**
   - CrashLab distinguishes between:
     - execution failures
     - timeout instability
     - parse/schema failures
     - evaluated but unsafe or low-quality responses
   - This prevents misleading scores when the underlying run is not trustworthy.

5. **Family-specific evaluation**
   - The evaluator routes the parsed output to a family-specific rubric.
   - Examples:
     - `agent_orchestrator`: routing, ambiguity handling, unsafe shortcut resistance
     - `analysis_pipeline`: schema correctness, grounded summary, weak-evidence handling
     - `rag_assistant`: groundedness and context-bound behavior
     - `general_chatbot`: instruction following and refusal behavior

6. **Trust label assignment**
   - After case execution, the runner aggregates results and assigns a trust label such as:
     - `Trusted`
     - `Needs Review`
     - `Parse Failed`
     - `Execution Failed`
     - `Execution Unstable`
     - `Unsafe / Ungrounded`

7. **Report export**
   - Completed runs can be exported as:
     - Markdown
     - JSON
     - CSV
   - Reports include target metadata, suite source, trust label, score, case outcomes, and selected runtime metadata.

## Why the Design Matters
CrashLab is intentionally not a universal agent benchmark.

Its main design claim is narrower and more defensible:
**workflow evaluation should depend on target role, output expectations, and observable failure modes.**

That is why the system uses:
- target families
- explicit parse failure handling
- risk-weighted case scoring
- trust labels instead of unconditional scores
