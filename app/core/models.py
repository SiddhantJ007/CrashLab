from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TargetProfile(BaseModel):
    family: str = "general_chatbot"
    domain: str = "general"
    capabilities: List[str] = Field(default_factory=list)
    supports_tools: bool = False


class TargetStatus(BaseModel):
    code: str
    label: str
    detail: str = ""
    usable: bool = False

    @classmethod
    def ready(cls, detail: str = ""):
        return cls(code="ready", label="Ready", detail=detail, usable=True)

    @classmethod
    def missing_config(cls, detail: str):
        return cls(code="missing_config", label="Missing config", detail=detail, usable=False)

    @classmethod
    def unreachable(cls, detail: str):
        return cls(code="unreachable", label="Unreachable", detail=detail, usable=False)

    @classmethod
    def response_parse_failed(cls, detail: str):
        return cls(code="response_parse_failed", label="Response parse failed", detail=detail, usable=False)

    @classmethod
    def provider_quota_exceeded(cls, detail: str):
        return cls(code="provider_quota_exceeded", label="Provider quota exceeded", detail=detail, usable=False)

    @classmethod
    def disabled(cls, detail: str = "Target is disabled in configuration"):
        return cls(code="disabled", label="Disabled", detail=detail, usable=False)


class TargetSpecCase(BaseModel):
    case_id: str
    category: str
    prompt: str
    expected_behavior: str = ""
    failure_conditions: List[str] = Field(default_factory=list)
    success_label: str = ""
    failure_label: str = ""
    risk_weight: int = 1
    evaluator_hints: Dict[str, Any] = Field(default_factory=dict)


class TargetSpec(BaseModel):
    role: str = ""
    purpose: str = ""
    valid_task_types: List[str] = Field(default_factory=list)
    invalid_task_types: List[str] = Field(default_factory=list)
    expected_output_style: str = ""
    expected_output_schema: Dict[str, Any] = Field(default_factory=dict)
    critical_failure_modes: List[str] = Field(default_factory=list)
    demo_suite: List[TargetSpecCase] = Field(default_factory=list)
    challenge_suite: List[TargetSpecCase] = Field(default_factory=list)
    full_suite: List[TargetSpecCase] = Field(default_factory=list)


class Target(BaseModel):
    id: str
    name: str
    kind: str
    platform: str = ""
    description: str = ""
    enabled: bool = True
    target_source: str = "bootstrap_targets_json"
    profile: TargetProfile = Field(default_factory=TargetProfile)
    target_spec: TargetSpec = Field(default_factory=TargetSpec)
    settings: Dict[str, Any] = Field(default_factory=dict)
    last_status: Optional[TargetStatus] = None
