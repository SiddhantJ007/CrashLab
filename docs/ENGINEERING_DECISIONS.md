# Engineering Decisions

This document records the main decisions behind CrashLab v1.1.

## 1. FastAPI monolith for v1
Chosen for speed, lower deployment complexity, and easier debugging.

## 2. Target-aware evaluation instead of generic chatbot scoring
Different workflow families need different expectations. This makes scores more defensible.

## 3. Conservative trust labels
A normal-looking score on an execution or parse failure would be misleading. Trust labels were treated as first-class product output.

## 4. Render over Vercel
Vercel was a poor fit for local writable SQLite persistence. Render fit the Python web-service model better.

## 5. Supabase over local hosted SQLite
Render free did not provide dependable persistence for CrashLab’s hosted shared-state use case. Supabase was the pragmatic hosted persistence solution.

## 6. Langflow deferred, Dify selected
Langflow required a separate hosted service and ran into runtime/dependency/memory/port issues during deployment attempts. Dify was selected as the second v1.1 platform to keep the project shippable.

## 7. SQLite fallback retained
SQLite remains useful for local development, tests, and simple offline use.

## 8. Intelligence layer kept assistive, not magical
The OpenAI-backed planner helps suggest families and test plans, but the system does not claim universal autonomous understanding of arbitrary agents.
