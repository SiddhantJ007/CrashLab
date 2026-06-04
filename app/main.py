import os
import re
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.core.config import load_targets
from app.core.planner import generate_target_plan, latest_probe_or_none, resolve_suite_for_target, run_probe, suite_preview, target_side_effect_warning
from app.core.registry import build_registry
from app.core.runner import build_run_csv, build_run_export, build_run_markdown_summary, compare_latest, get_run, history_runs, start_run
from app.core.store import get_active_test_plan, init_db, latest_plan_summaries, save_configured_target
from app.core.tests import FAMILY_DEFAULT_SPECS

BASE_DIR = Path(__file__).resolve().parent
TARGETS_PATH = BASE_DIR.parent / "targets.json"


class TargetCreateInput(BaseModel):
    name: str
    platform: str
    base_url: str
    flow_or_endpoint: str
    api_key_env: str = ""
    description: str = ""
    family: str
    expected_output_style: str = "text"
    enabled: bool = True
    timeout_seconds: int = 60
    side_effects: str = "unknown"
    output_component: str = ""
    preferred_output_index: Optional[int] = None
    preferred_nested_index: Optional[int] = None
    preferred_result_key: str = ""


class TargetAnalysisInput(BaseModel):
    name: str = ""
    platform: str = ""
    description: str = ""
    expected_output_style: str = "text"
    family: str = ""
    capabilities: list[str] = []
    side_effects: str = "unknown"


def load_local_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_local_env(BASE_DIR.parent / ".env")
    init_db()
    reload_registry(app)
    yield


app = FastAPI(title="CrashLab", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def reload_registry(fastapi_app: FastAPI):
    fastapi_app.state.registry = build_registry(load_targets(TARGETS_PATH))


def registry():
    return app.state.registry


def visible_targets():
    cards = {
        key: value
        for key, value in registry().list_targets().items()
        if value.get("kind") != "webarena"
    }
    latest_by_target = {}
    for run in history_runs():
        latest_by_target.setdefault(run["target_id"], run)
    plan_summaries = latest_plan_summaries()
    for target_id, card in cards.items():
        latest = latest_by_target.get(target_id)
        if latest:
            card["last_run"] = {
                "trust_label": latest.get("trust_label"),
                "score_display": latest.get("score_display"),
                "summary": latest.get("summary"),
                "outcome": latest.get("outcome"),
            }
        else:
            card["last_run"] = None
        demo_key = f"{target_id}::demo"
        card["plan_summary"] = plan_summaries.get(demo_key)
        card["probe_summary"] = latest_probe_or_none(target_id)
        resolved = resolve_suite_for_target(registry().get(target_id).target, "demo")
        card["suite_source"] = resolved.get("source") or "none"
        card["run_blocked_reason"] = None if resolved.get("ok") else resolved.get("message")
        card["warning"] = target_side_effect_warning(registry().get(target_id).target)
    return cards


def normalize_platform(platform: str) -> str:
    raw = (platform or "").strip().lower()
    if raw == "flowise":
        return "flowise"
    if raw == "langflow":
        return "langflow"
    return "custom_api"


def target_defaults_for_family(family: str):
    defaults = {
        "agent_orchestrator": {
            "domain": "software_workflow",
            "capabilities": ["routing", "structured_output", "multi_step_reasoning"],
            "supports_tools": True,
        },
        "analysis_pipeline": {
            "domain": "community_feedback",
            "capabilities": ["sentiment_labeling", "structured_summary", "action_recommendation", "grounded_text_analysis"],
            "supports_tools": False,
        },
        "rag_assistant": {
            "domain": "document_qa",
            "capabilities": ["grounded_answers", "citation_behavior", "context_boundary"],
            "supports_tools": False,
        },
        "general_chatbot": {
            "domain": "general_assistance",
            "capabilities": ["instruction_following", "format_consistency", "guardrail_behavior"],
            "supports_tools": False,
        },
        "custom_or_unknown": {
            "domain": "custom_workflow",
            "capabilities": [],
            "supports_tools": False,
        },
    }
    return defaults.get(family, defaults["custom_or_unknown"])


def _slugify_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_") or f"target_{uuid.uuid4().hex[:6]}"


def _unique_target_id(base_id: str) -> str:
    existing = set(visible_targets().keys())
    if base_id not in existing:
        return base_id
    index = 2
    while f"{base_id}_{index}" in existing:
        index += 1
    return f"{base_id}_{index}"


def build_target_payload(form: TargetCreateInput):
    kind = normalize_platform(form.platform)
    target_id = _unique_target_id(_slugify_name(form.name))
    family_defaults = target_defaults_for_family(form.family)
    settings = {
        "base_url": form.base_url.strip(),
        "read_timeout_seconds": int(form.timeout_seconds),
        "timeout_retry_count": 0,
        "side_effects": form.side_effects,
    }
    flow_or_endpoint = form.flow_or_endpoint.strip()
    api_key_env = form.api_key_env.strip()
    if kind == "flowise":
        settings.update(
            {
                "flow_id": flow_or_endpoint,
                "auth_header": "Authorization",
                "auth_token_env": api_key_env,
                "connect_timeout_seconds": 10,
                "timeout_retry_count": 1,
            }
        )
    elif kind == "langflow":
        settings.update(
            {
                "flow_id": flow_or_endpoint,
                "api_key_env": api_key_env,
                "input_type": "chat",
                "output_type": "chat",
                "session_id": f"crashlab-{target_id}",
                "input_format": "plain_text",
            }
        )
    else:
        settings.update(
            {
                "endpoint_path": flow_or_endpoint,
                "api_key_env": api_key_env,
            }
        )
    if form.output_component.strip():
        settings["output_component"] = form.output_component.strip()
    if form.preferred_output_index is not None:
        settings["preferred_output_index"] = form.preferred_output_index
    if form.preferred_nested_index is not None:
        settings["preferred_nested_index"] = form.preferred_nested_index
    if form.preferred_result_key.strip():
        settings["preferred_result_key"] = form.preferred_result_key.strip()

    return {
        "id": target_id,
        "name": form.name.strip(),
        "kind": kind,
        "platform": {"flowise": "Flowise", "langflow": "Langflow", "custom_api": "Custom API"}[kind],
        "description": form.description.strip(),
        "enabled": bool(form.enabled),
        "target_source": "onboarded_sqlite",
        "profile": {
            "family": form.family,
            "domain": family_defaults["domain"],
            "capabilities": family_defaults["capabilities"],
            "supports_tools": family_defaults["supports_tools"],
        },
        "target_spec": {
            "role": FAMILY_DEFAULT_SPECS.get(form.family, {}).get("role", form.family.replace("_", " ")),
            "purpose": form.description.strip(),
            "expected_output_style": form.expected_output_style,
            "expected_output_schema": FAMILY_DEFAULT_SPECS.get(form.family, {}).get("expected_output_schema", {}),
        },
        "settings": settings,
    }


def heuristic_family_suggestion(payload: TargetAnalysisInput):
    text = " ".join([payload.name, payload.description, payload.platform, payload.expected_output_style, " ".join(payload.capabilities)]).lower()
    if payload.family:
        family = payload.family
    elif any(token in text for token in ["route", "worker", "review workflow", "supervisor", "merge"]):
        family = "agent_orchestrator"
    elif any(token in text for token in ["feedback", "sentiment", "summary", "analy"]):
        family = "analysis_pipeline"
    elif any(token in text for token in ["context", "citation", "retrieval", "document qa"]):
        family = "rag_assistant"
    else:
        family = "general_chatbot"
    template = FAMILY_DEFAULT_SPECS[family]
    return {
        "mode": "manual_template_suggestion",
        "suggested_family": family,
        "suggested_risk_areas": template.get("critical_failure_modes", []),
        "suggested_demo_cases": [case["category"] for case in template.get("demo_suite", [])[:5]],
        "suggested_full_cases": [case["category"] for case in template.get("full_suite", [])[:10]],
        "expected_output_schema": template.get("expected_output_schema", {}),
        "warning": "This is a suggestion layer, not a guarantee of correct family classification.",
    }


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "targets": list(visible_targets().values()),
            "asset_version": "r5-final-ui-4",
        },
    )


@app.get("/api/targets")
def api_targets():
    return visible_targets()


@app.post("/api/targets")
def api_create_target(payload: TargetCreateInput):
    target = build_target_payload(payload)
    save_configured_target(target)
    reload_registry(app)
    return {"ok": True, "target_id": target["id"], "target": visible_targets().get(target["id"])}


@app.post("/api/targets/analyze")
def api_analyze_target(payload: TargetAnalysisInput):
    return heuristic_family_suggestion(payload)


@app.get("/api/targets/{target_id}/suite-preview")
def api_suite_preview(target_id: str, mode: str = "demo"):
    target = registry().get(target_id).target
    if target.kind == "webarena":
        raise HTTPException(status_code=404, detail="Unknown target")
    return suite_preview(target, mode)


@app.post("/api/targets/{target_id}/plans/generate")
def api_generate_plan(target_id: str):
    adapter = registry().get(target_id)
    target = adapter.target
    probe_summary = latest_probe_or_none(target.id)
    result = generate_target_plan(target, probe_summary=probe_summary)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("message") or "Could not generate a test plan.")
    return result


@app.post("/api/targets/{target_id}/probe")
def api_probe_target(target_id: str):
    adapter = registry().get(target_id)
    if target_side_effect_warning(adapter.target):
        # Probes are intentionally read-only from CrashLab's perspective, but we still expose
        # the side-effect warning so the UI can keep that risk visible.
        pass
    summary = run_probe(adapter)
    return {"warning": target_side_effect_warning(adapter.target), "probe": summary}


@app.post("/api/run/{target_id}")
def api_run(target_id: str, mode: str = "demo"):
    targets = visible_targets()
    if target_id not in targets:
        raise HTTPException(status_code=404, detail="Unknown target")
    if not targets[target_id]["status"]["usable"]:
        raise HTTPException(status_code=409, detail=targets[target_id]["status"]["detail"] or "Target is not ready to run.")
    if mode not in set(targets[target_id].get("available_modes", ["demo"])):
        raise HTTPException(status_code=400, detail=f"Mode must be one of: {', '.join(targets[target_id].get('available_modes', ['demo']))}.")
    adapter = registry().get(target_id)
    suite_selection = resolve_suite_for_target(adapter.target, mode)
    if not suite_selection.get("ok"):
        raise HTTPException(status_code=409, detail=suite_selection.get("message") or "Target requires a reviewed test plan before evaluation.")
    run_id = str(uuid.uuid4())[:8]
    start_run(run_id, adapter, mode=mode, suite_selection=suite_selection)
    return {"run_id": run_id, "target_id": target_id, "mode": mode, "suite_source": suite_selection.get("source"), "plan_id": suite_selection.get("plan_id")}


@app.get("/api/run/{run_id}")
def api_run_status(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Unknown run")
    return run


@app.get("/api/compare")
def api_compare():
    return compare_latest()


@app.get("/api/history")
def api_history():
    return {"runs": history_runs()}


@app.get("/api/run/{run_id}/export.json")
def api_run_export_json(run_id: str):
    payload = build_run_export(run_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Unknown run")
    return Response(
        content=json_bytes(payload),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="crashlab-run-{run_id}.json"'},
    )


@app.get("/api/run/{run_id}/export.csv")
def api_run_export_csv(run_id: str):
    content = build_run_csv(run_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Unknown run")
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="crashlab-run-{run_id}.csv"'},
    )


@app.get("/api/run/{run_id}/summary.md")
def api_run_summary_markdown(run_id: str):
    content = build_run_markdown_summary(run_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Unknown run")
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="crashlab-run-{run_id}.md"'},
    )


@app.get("/health")
def health():
    return {"ok": True, "targets": len(visible_targets())}


def json_bytes(payload):
    import json

    return json.dumps(payload, indent=2).encode("utf-8")
