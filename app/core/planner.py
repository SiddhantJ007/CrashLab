import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.adapters.base import TargetExecutionError
from app.core.models import Target
from app.core.store import get_active_test_plan, get_probe_summary, save_probe_summary, save_test_plan
from app.core.tests import FAMILY_DEFAULT_SPECS, build_test_suite, effective_target_spec

LLM_PLANNER_MODEL = os.getenv("OPENAI_PLANNER_MODEL", "gpt-4.1-mini")


# Planner helpers normalize runtime config so generated plans, run exports, and reports can
# show exactly which base URL and flow or endpoint path were used for a target.
def target_runtime_config(target: Target) -> Dict[str, Any]:
    settings = target.settings or {}
    return {
        "base_url": settings.get("base_url"),
        "flow_id": settings.get("flow_id"),
        "endpoint_path": settings.get("endpoint_path"),
        "side_effects": settings.get("side_effects", "unknown"),
    }


def target_endpoint_label(target: Target) -> str:
    runtime = target_runtime_config(target)
    return runtime.get("flow_id") or runtime.get("endpoint_path") or "n/a"


def target_side_effect_warning(target: Target) -> str:
    side_effects = str(target.settings.get("side_effects", "unknown")).lower()
    if side_effects in {"yes", "unknown", "may_have_side_effects"}:
        return "Use a safe test instance or dry-run mode. CrashLab evaluates observable API behavior and cannot guarantee hidden side effects."
    return ""


def plan_cases_from_suite(cases: List[Any]) -> List[Dict[str, Any]]:
    normalized = []
    for case in cases:
        if hasattr(case, "model_dump"):
            normalized.append(case.model_dump())
        else:
            normalized.append(dict(case))
    return normalized


# Suite resolution is prioritized: approved generated plan -> explicit target_spec ->
# default family template. custom_or_unknown is blocked unless a reviewed plan exists.
def resolve_suite_for_target(target: Target, mode: str) -> Dict[str, Any]:
    approved_plan = get_active_test_plan(target.id, mode)
    if approved_plan:
        return {
            "ok": True,
            "source": approved_plan["source"],
            "plan_id": approved_plan["plan_id"],
            "approved": approved_plan.get("approved", True),
            "mode": mode,
            "cases": approved_plan.get("cases", []),
            "target_profile_summary": approved_plan.get("target_profile_summary", {}),
            "message": f"Using approved {approved_plan['source']} plan.",
        }

    raw_spec = target.target_spec
    if mode == "challenge" and raw_spec.challenge_suite:
        return {
            "ok": True,
            "source": "explicit_target_spec",
            "plan_id": None,
            "approved": True,
            "mode": mode,
            "cases": plan_cases_from_suite(raw_spec.challenge_suite),
            "target_profile_summary": _plan_profile_summary(target),
            "message": "Using the target's explicit challenge suite.",
        }
    if mode == "demo" and raw_spec.demo_suite:
        return {
            "ok": True,
            "source": "explicit_target_spec",
            "plan_id": None,
            "approved": True,
            "mode": mode,
            "cases": plan_cases_from_suite(raw_spec.demo_suite),
            "target_profile_summary": _plan_profile_summary(target),
            "message": "Using the target's explicit demo suite.",
        }
    if mode == "full" and raw_spec.full_suite:
        return {
            "ok": True,
            "source": "explicit_target_spec",
            "plan_id": None,
            "approved": True,
            "mode": mode,
            "cases": plan_cases_from_suite(raw_spec.full_suite),
            "target_profile_summary": _plan_profile_summary(target),
            "message": "Using the target's explicit full suite.",
        }

    if target.profile.family == "custom_or_unknown":
        return {
            "ok": False,
            "source": None,
            "plan_id": None,
            "approved": False,
            "mode": mode,
            "cases": [],
            "target_profile_summary": _plan_profile_summary(target),
            "message": "Custom/unknown targets require a reviewed test plan before evaluation.",
        }

    template_cases = build_test_suite(target, mode)
    return {
        "ok": True,
        "source": "default_family_template",
        "plan_id": None,
        "approved": True,
        "mode": mode,
        "cases": template_cases,
        "target_profile_summary": _plan_profile_summary(target),
        "message": "Using the default family template.",
    }


def suite_preview(target: Target, mode: str) -> Dict[str, Any]:
    resolved = resolve_suite_for_target(target, mode)
    return {
        "target_id": target.id,
        "target_name": target.name,
        "mode": mode,
        "source": resolved.get("source") or "none",
        "approved": resolved.get("approved", False),
        "plan_id": resolved.get("plan_id"),
        "message": resolved.get("message"),
        "cases": resolved.get("cases", []),
        "target_profile_summary": resolved.get("target_profile_summary", {}),
        "warning": target_side_effect_warning(target),
    }


def _plan_profile_summary(target: Target, probe_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    spec = effective_target_spec(target)
    summary = {
        "family": target.profile.family,
        "purpose": spec.purpose or target.description,
        "expected_input": spec.valid_task_types[:4],
        "expected_output": spec.expected_output_style or target.target_spec.expected_output_style,
        "risk_focus": spec.critical_failure_modes[:6],
        "probe_style_hint": probe_summary.get("response_style") if probe_summary else None,
    }
    return summary


def build_default_plan_bundle(target: Target, probe_summary: Optional[Dict[str, Any]] = None, source: str = "manual_adapted") -> Dict[str, Any]:
    spec = effective_target_spec(target)
    profile_summary = _plan_profile_summary(target, probe_summary)
    plans = []
    now = int(time.time())
    for mode, suite in (("demo", spec.demo_suite), ("full", spec.full_suite)):
        if not suite:
            continue
        cases = plan_cases_from_suite(suite)
        if target.description:
            for case in cases:
                case["expected_behavior"] = case.get("expected_behavior") or f"Stay aligned with target purpose: {target.description}"
        plans.append(
            {
                "plan_id": f"plan_{uuid.uuid4().hex[:10]}",
                "target_id": target.id,
                "target_name": target.name,
                "platform": target.platform or target.kind,
                "family": target.profile.family,
                "mode": mode,
                "source": source,
                "approved": True,
                "created_at": now,
                "target_profile_summary": profile_summary,
                "cases": cases,
            }
        )
    return {"source": source, "target_profile": profile_summary, "plans": plans, "message": "Generated a local plan from the family template."}


def planner_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


# The LLM-assisted planner is optional. If it is unavailable or fails, CrashLab stores a
# safe local adaptation instead of blocking normal operation for shipped targets.
def generate_target_plan(target: Target, probe_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if target.profile.family == "custom_or_unknown" and not planner_available():
        return {"ok": False, "message": "Custom/unknown targets need a reviewed test plan. Add one manually or enable OPENAI_API_KEY for LLM-assisted planning."}

    if planner_available():
        try:
            llm_bundle = _generate_llm_plan_bundle(target, probe_summary)
            for plan in llm_bundle["plans"]:
                save_test_plan(plan)
            return {"ok": True, **llm_bundle}
        except Exception as exc:
            fallback_source = "probe_assisted" if probe_summary else "manual_adapted"
            fallback = build_default_plan_bundle(target, probe_summary=probe_summary, source=fallback_source)
            for plan in fallback["plans"]:
                save_test_plan(plan)
            return {"ok": True, **fallback, "message": f"LLM planning failed; fell back to a local family-template adaptation. {exc}"}

    fallback_source = "probe_assisted" if probe_summary else "manual_adapted"
    fallback = build_default_plan_bundle(target, probe_summary=probe_summary, source=fallback_source)
    for plan in fallback["plans"]:
        save_test_plan(plan)
    return {"ok": True, **fallback}


# When enabled, the planner asks the model for strict JSON only. The returned suites are
# stored as target-specific test plans rather than mutating the built-in family templates.
def _generate_llm_plan_bundle(target: Target, probe_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    family_defaults = FAMILY_DEFAULT_SPECS.get(target.profile.family, {})
    prompt = {
        "target_name": target.name,
        "platform": target.platform or target.kind,
        "family": target.profile.family,
        "description": target.description,
        "expected_output_style": target.target_spec.expected_output_style or effective_target_spec(target).expected_output_style,
        "capabilities": target.profile.capabilities,
        "side_effect_flags": target.settings.get("side_effects", "unknown"),
        "base_family_template": {
            "demo_suite": family_defaults.get("demo_suite", []),
            "full_suite": family_defaults.get("full_suite", []),
        },
        "probe_summary": probe_summary,
    }
    system_prompt = (
        "You are generating a target-specific CrashLab test plan for an API-accessible AI workflow. "
        "Return strict JSON only with keys target_profile, demo_suite, and full_suite. "
        "Each case must include case_id, category, prompt, expected_behavior, failure_conditions, success_label, failure_label, risk_weight, and evaluator_hints."
    )
    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_PLANNER_MODEL,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": json.dumps(prompt)}]},
            ],
            "text": {"format": {"type": "json_object"}},
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    text = _responses_text(payload)
    parsed = json.loads(text)
    source = "probe_assisted" if probe_summary else "llm_generated"
    profile_summary = parsed.get("target_profile") or _plan_profile_summary(target, probe_summary)
    now = int(time.time())
    plans = []
    for mode_key, suite_key in (("demo", "demo_suite"), ("full", "full_suite")):
        cases = parsed.get(suite_key) or []
        plans.append(
            {
                "plan_id": f"plan_{uuid.uuid4().hex[:10]}",
                "target_id": target.id,
                "target_name": target.name,
                "platform": target.platform or target.kind,
                "family": target.profile.family,
                "mode": mode_key,
                "source": source,
                "approved": True,
                "created_at": now,
                "target_profile_summary": profile_summary,
                "cases": cases,
            }
        )
    return {"source": source, "target_profile": profile_summary, "plans": plans, "message": "Generated a target-specific plan with the LLM planner."}


def _responses_text(payload: Dict[str, Any]) -> str:
    collected: List[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for chunk in item.get("content", []):
            if chunk.get("type") in {"output_text", "text"} and chunk.get("text"):
                collected.append(chunk["text"])
    if collected:
        return "\n".join(collected)
    return payload.get("output_text") or "{}"


def build_probe_prompt(target: Target) -> str:
    family = target.profile.family
    if family == "analysis_pipeline":
        return "Analyze this short feedback: The login page is slow but the new UI is clean."
    if family == "agent_orchestrator":
        return "A backend fix is ready but CI is failing. State the next workflow step."
    if family == "rag_assistant":
        return "Context: The retention window is 30 days. Question: How long is the retention window?"
    return "Reply in exactly two bullet points: why staging environments matter."


# Probe calls are intentionally lightweight and safe. They are optional evidence used to
# summarize output style and shape; they do not replace a real evaluation run.
def run_probe(adapter) -> Dict[str, Any]:
    target = adapter.target
    prompt = build_probe_prompt(target)
    try:
        result = adapter.execute(prompt)
    except TargetExecutionError as exc:
        summary = {
            "target_id": target.id,
            "prompt": prompt,
            "ok": False,
            "error": exc.detail,
            "response_style": "execution_failed",
            "captured_at": int(time.time()),
        }
        save_probe_summary(target.id, summary)
        return summary

    text = (result.get("text") or "").strip()
    meta = result.get("meta", {})
    parsed_keys = []
    response_style = "text"
    langflow = meta.get("langflow", {}) if isinstance(meta, dict) else {}
    if langflow.get("parsed_json"):
        parsed_keys = list(langflow["parsed_json"].keys())
        response_style = "json"
    elif text.startswith("{"):
        response_style = "json_like"
    summary = {
        "target_id": target.id,
        "prompt": prompt,
        "ok": bool(result.get("ok")),
        "response_preview": text[:320],
        "response_style": response_style,
        "parsed_keys": parsed_keys,
        "meta_summary": meta.get("response_summary") if isinstance(meta, dict) else {},
        "captured_at": int(time.time()),
    }
    save_probe_summary(target.id, summary)
    return summary


def latest_probe_or_none(target_id: str) -> Optional[Dict[str, Any]]:
    return get_probe_summary(target_id)