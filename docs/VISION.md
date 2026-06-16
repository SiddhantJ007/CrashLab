# CrashLab Vision

CrashLab is intended to become a reusable evaluation layer for API-accessible LLM workflows.

## Core Idea
Modern AI products increasingly rely on workflows rather than a single model call. These workflows route tasks, call tools, summarize evidence, retrieve context, and return structured outputs. They are easy to build and difficult to validate systematically.

CrashLab exists to make those workflows testable.

## Product Direction
CrashLab focuses on:
- target-aware evaluation rather than one-size-fits-all scoring
- reusable adapters for workflow platforms
- family-specific testing logic
- generated or adapted test plans when metadata is incomplete
- explicit trust labels instead of false benchmark certainty

## v1.1 Positioning
CrashLab v1.1 is a working MVP/demo with:
- Flowise integration
- Dify integration
- dynamic target onboarding
- OpenAI-assisted target analysis and test-plan generation
- Render deployment
- Supabase-backed hosted persistence

It is not yet a fully multi-tenant enterprise evaluation platform.

## Long-Term Goal
The longer-term goal is to make CrashLab a control plane for evaluating agentic workflows across:
- task completion
- safety behavior
- grounding quality
- schema compliance
- operational stability
- regression drift over workflow versions
