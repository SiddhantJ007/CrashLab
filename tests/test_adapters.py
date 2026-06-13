from app.adapters.custom_api import CustomAPIAdapter
from app.adapters.flowise import FlowiseAdapter
from app.adapters.langflow import LangflowAdapter

from tests.helpers import make_target


def test_flowise_adapter_parses_fixture_response(monkeypatch):
    target = make_target(
        kind="flowise",
        platform="Flowise",
        profile={"family": "agent_orchestrator", "domain": "software_workflow", "capabilities": [], "supports_tools": True},
        target_spec={"role": "orchestrator", "purpose": "route work", "expected_output_style": "structured_answer", "demo_suite": [], "full_suite": [], "challenge_suite": []},
        settings={"base_url": "https://example.com", "flow_id": "flow-1", "auth_token_env": "FLOWISE_API_KEY", "side_effects": "no"},
    )
    adapter = FlowiseAdapter(target)
    monkeypatch.setattr(adapter, "request_json", lambda *args, **kwargs: ({
        "text": "Route to backend review and rerun auth tests before merge.",
        "executionId": "exec-1",
        "chatId": "chat-1",
        "chatMessageId": "msg-1",
        "sessionId": "sess-1",
        "agentFlowExecutedData": [{"nodeLabel": "Supervisor", "nodeType": "agent"}],
    }, 1))
    result = adapter.execute("prompt")
    assert result["ok"] is True
    assert "backend review" in result["text"]
    assert result["meta"]["flowise"]["execution_id"] == "exec-1"


def test_langflow_adapter_parses_selected_json_output(monkeypatch):
    target = make_target(
        kind="langflow",
        platform="Langflow",
        profile={"family": "analysis_pipeline", "domain": "community_feedback", "capabilities": [], "supports_tools": False},
        target_spec={
            "role": "analysis",
            "purpose": "feedback analysis",
            "expected_output_style": "json",
            "expected_output_schema": {"sentiment": "...", "summary": "...", "action_item": "..."},
            "demo_suite": [],
            "full_suite": [],
            "challenge_suite": [],
        },
        settings={
            "base_url": "https://example.com",
            "flow_id": "flow-2",
            "output_component": "Chat Output",
            "side_effects": "no",
        },
    )
    adapter = LangflowAdapter(target)
    monkeypatch.setattr(adapter, "request_json", lambda *args, **kwargs: ({
        "outputs": [
            {
                "outputs": [
                    {
                        "component_display_name": "Chat Output",
                        "results": {
                            "message": {
                                "sentiment": "Mixed",
                                "summary": "Users like speed but exports fail.",
                                "action_item": "Prioritize export reliability.",
                                "confidence": "High",
                                "evidence_note": "Cleaner dashboard and failing exports are both mentioned."
                            }
                        },
                    }
                ]
            }
        ]
    }, 1))
    result = adapter.execute("prompt")
    assert result["ok"] is True
    assert "Mixed" in result["text"]
    assert result["meta"]["langflow"]["candidate_count"] >= 1
    assert result["meta"]["langflow"]["selected_path"]["component_label"] == "Chat Output"


def test_custom_api_adapter_parses_text_candidate(monkeypatch):
    target = make_target(
        kind="custom_api",
        platform="Custom API",
        profile={"family": "general_chatbot", "domain": "general_assistance", "capabilities": [], "supports_tools": False},
        target_spec={"role": "chatbot", "purpose": "reply", "expected_output_style": "text", "demo_suite": [], "full_suite": [], "challenge_suite": []},
        settings={"base_url": "https://example.com", "endpoint_path": "/run", "side_effects": "no"},
    )
    adapter = CustomAPIAdapter(target)
    monkeypatch.setattr(adapter, "request_json", lambda *args, **kwargs: ({"message": {"text": "Hello from the custom API."}}, 1))
    result = adapter.execute("prompt")
    assert result["ok"] is True
    assert result["text"] == "Hello from the custom API."


def test_flowise_adapter_can_resolve_runtime_settings_from_env(monkeypatch):
    monkeypatch.setenv("FLOWISE_BASE_URL", "https://flowise.example.com")
    monkeypatch.setenv("FLOWISE_FLOW_ID", "flow-env-1")
    target = make_target(
        kind="flowise",
        platform="Flowise",
        profile={"family": "agent_orchestrator", "domain": "software_workflow", "capabilities": [], "supports_tools": True},
        target_spec={"role": "orchestrator", "purpose": "route work", "expected_output_style": "structured_answer", "demo_suite": [], "full_suite": [], "challenge_suite": []},
        settings={"base_url": "", "flow_id": "", "base_url_env": "FLOWISE_BASE_URL", "flow_id_env": "FLOWISE_FLOW_ID", "auth_token_env": "FLOWISE_API_KEY", "side_effects": "no"},
    )
    adapter = FlowiseAdapter(target)
    assert adapter.missing_settings() == []
    assert adapter.endpoint_url() == "https://flowise.example.com/api/v1/prediction/flow-env-1"


def test_langflow_adapter_missing_config_mentions_env_vars():
    target = make_target(
        kind="langflow",
        platform="Langflow",
        profile={"family": "analysis_pipeline", "domain": "community_feedback", "capabilities": [], "supports_tools": False},
        target_spec={"role": "analysis", "purpose": "feedback analysis", "expected_output_style": "json", "demo_suite": [], "full_suite": [], "challenge_suite": []},
        settings={"base_url": "", "flow_id": "", "base_url_env": "LANGFLOW_BASE_URL", "flow_id_env": "LANGFLOW_FLOW_ID", "side_effects": "no"},
    )
    status = LangflowAdapter(target).readiness()
    assert status.code == "missing_config"
    assert "LANGFLOW_BASE_URL" in status.detail
    assert "LANGFLOW_FLOW_ID" in status.detail
