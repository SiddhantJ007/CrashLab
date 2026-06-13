from app.core.models import Target


def make_target(**overrides):
    payload = {
        "id": "test_target",
        "name": "Test Target",
        "kind": "custom_api",
        "platform": "Custom API",
        "description": "Test target",
        "enabled": True,
        "target_source": "test_fixture",
        "profile": {
            "family": "general_chatbot",
            "domain": "general_assistance",
            "capabilities": ["instruction_following"],
            "supports_tools": False,
        },
        "target_spec": {
            "role": "test role",
            "purpose": "test purpose",
            "expected_output_style": "text",
            "demo_suite": [],
            "full_suite": [],
            "challenge_suite": [],
        },
        "settings": {
            "base_url": "https://example.com",
            "endpoint_path": "/run",
            "side_effects": "no",
        },
    }
    for key, value in overrides.items():
        payload[key] = value
    return Target(**payload)
