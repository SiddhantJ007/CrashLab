from app.adapters.custom_api import CustomAPIAdapter
from app.adapters.dify import DifyAdapter
from app.adapters.flowise import FlowiseAdapter

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


def test_dify_adapter_parses_strict_json_answer(monkeypatch):
    target = make_target(
        kind="dify",
        platform="Dify",
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
            "base_url": "https://api.dify.example/v1",
            "endpoint_path": "/chat-messages",
            "api_key_env": "DIFY_API_KEY",
            "side_effects": "no",
        },
    )
    adapter = DifyAdapter(target)
    monkeypatch.setattr(adapter, "request_json", lambda *args, **kwargs: ({
        "event": "message",
        "task_id": "task-1",
        "message_id": "message-1",
        "conversation_id": "conversation-1",
        "mode": "chat",
        "answer": '{"sentiment":"Mixed","summary":"Users like speed but exports fail.","action_item":"Prioritize export reliability.","confidence":"High","evidence_note":"Both positive and negative evidence are mentioned."}',
        "metadata": {"usage": {"total_tokens": 42}},
    }, 1))
    result = adapter.execute("prompt")
    assert result["ok"] is True
    assert "Mixed" in result["text"]
    assert result["meta"]["dify"]["candidate_count"] >= 1
    assert result["meta"]["dify"]["conversation_id"] == "conversation-1"


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


def test_dify_adapter_missing_config_mentions_env_vars():
    target = make_target(
        kind="dify",
        platform="Dify",
        profile={"family": "analysis_pipeline", "domain": "community_feedback", "capabilities": [], "supports_tools": False},
        target_spec={"role": "analysis", "purpose": "feedback analysis", "expected_output_style": "json", "demo_suite": [], "full_suite": [], "challenge_suite": []},
        settings={"base_url": "", "endpoint_path": "/chat-messages", "base_url_env": "DIFY_BASE_URL", "api_key_env": "DIFY_API_KEY", "side_effects": "no"},
    )
    status = DifyAdapter(target).readiness()
    assert status.code == "missing_config"
    assert "DIFY_BASE_URL" in status.detail
    assert "DIFY_API_KEY" in status.detail


def test_flowise_adapter_accepts_full_prediction_url_in_base_url():
    target = make_target(
        kind="flowise",
        platform="Flowise",
        profile={"family": "agent_orchestrator", "domain": "software_workflow", "capabilities": [], "supports_tools": True},
        target_spec={"role": "orchestrator", "purpose": "route work", "expected_output_style": "structured_answer", "demo_suite": [], "full_suite": [], "challenge_suite": []},
        settings={
            "base_url": "https://cloud.flowiseai.com/api/v1/prediction/ac34cd2d-f5f8-4edb-8398-0e1345c0cf58",
            "flow_id": "ac34cd2d-f5f8-4edb-8398-0e1345c0cf58",
            "auth_token_env": "FLOWISE_API_KEY",
            "side_effects": "no",
        },
    )
    adapter = FlowiseAdapter(target)
    assert adapter.missing_settings() == []
    assert adapter.endpoint_url() == "https://cloud.flowiseai.com/api/v1/prediction/ac34cd2d-f5f8-4edb-8398-0e1345c0cf58"
    assert adapter.probe_url() == "https://cloud.flowiseai.com"


def test_dify_adapter_prefers_nested_structured_output(monkeypatch):
    target = make_target(
        kind="dify",
        platform="Dify",
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
            "base_url": "https://api.dify.example/v1",
            "endpoint_path": "/workflows/run",
            "api_key_env": "DIFY_API_KEY",
            "side_effects": "no",
        },
    )
    adapter = DifyAdapter(target)
    monkeypatch.setattr(adapter, "request_json", lambda *args, **kwargs: ({
        "event": "workflow_finished",
        "workflow_run": {
            "outputs": {
                "analysis": "```json\n{\"sentiment\":\"Mixed\",\"summary\":\"Search improved but exports fail.\",\"action_item\":\"Prioritize export fixes.\"}\n```"
            }
        },
    }, 1))
    result = adapter.execute("prompt")
    assert result["ok"] is True
    assert "Prioritize export fixes" in result["text"]
    assert result["meta"]["dify"]["selection_reason"].startswith("configured_schema")
