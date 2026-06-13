from app.core.planner import resolve_suite_for_target
from app.core.store import save_test_plan

from tests.helpers import make_target


def test_resolve_suite_prefers_approved_plan():
    target = make_target(profile={"family": "analysis_pipeline", "domain": "community_feedback", "capabilities": [], "supports_tools": False})
    save_test_plan(
        {
            "plan_id": "plan_approved_demo",
            "target_id": target.id,
            "mode": "demo",
            "source": "llm_generated",
            "approved": True,
            "created_at": 1,
            "target_profile_summary": {"family": "analysis_pipeline"},
            "cases": [{"case_id": "P01", "category": "custom", "prompt": "hi"}],
        }
    )
    resolved = resolve_suite_for_target(target, "demo")
    assert resolved["ok"] is True
    assert resolved["source"] == "llm_generated"
    assert resolved["plan_id"] == "plan_approved_demo"
    assert resolved["cases"][0]["case_id"] == "P01"


def test_resolve_suite_uses_explicit_target_spec_when_present():
    target = make_target(
        profile={"family": "general_chatbot", "domain": "general_assistance", "capabilities": [], "supports_tools": False},
        target_spec={
            "role": "chatbot",
            "purpose": "answer questions",
            "expected_output_style": "text",
            "demo_suite": [{"case_id": "D01", "category": "instruction_following", "prompt": "hello"}],
            "full_suite": [],
            "challenge_suite": [],
        },
    )
    resolved = resolve_suite_for_target(target, "demo")
    assert resolved["ok"] is True
    assert resolved["source"] == "explicit_target_spec"
    assert resolved["cases"][0]["case_id"] == "D01"


def test_resolve_suite_falls_back_to_default_family_template():
    target = make_target(
        profile={"family": "general_chatbot", "domain": "general_assistance", "capabilities": [], "supports_tools": False},
        target_spec={"role": "", "purpose": "", "expected_output_style": "text", "demo_suite": [], "full_suite": [], "challenge_suite": []},
    )
    resolved = resolve_suite_for_target(target, "demo")
    assert resolved["ok"] is True
    assert resolved["source"] == "default_family_template"
    assert len(resolved["cases"]) >= 1


def test_resolve_suite_blocks_custom_unknown_without_plan():
    target = make_target(
        profile={"family": "custom_or_unknown", "domain": "custom_workflow", "capabilities": [], "supports_tools": False},
        target_spec={"role": "", "purpose": "", "expected_output_style": "text", "demo_suite": [], "full_suite": [], "challenge_suite": []},
    )
    resolved = resolve_suite_for_target(target, "demo")
    assert resolved["ok"] is False
    assert "reviewed test plan" in resolved["message"].lower()
