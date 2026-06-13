from app.adapters.custom_api import CustomAPIAdapter
from app.adapters.flowise import FlowiseAdapter
from app.adapters.langflow import LangflowAdapter
from app.core.models import Target
from app.core.tests import available_modes_for_target, effective_target_spec

try:
    from app.adapters.webarena import WebArenaAdapter
except ModuleNotFoundError:  # Public v1 does not ship WebArena in the live product flow.
    WebArenaAdapter = None


def platform_label_for(target: Target) -> str:
    if target.platform:
        return target.platform
    mapping = {
        "flowise": "Flowise",
        "langflow": "Langflow",
        "custom_api": "Custom API",
        "webarena": "WebArena",
    }
    return mapping.get(target.kind, target.kind.replace("_", " ").title())


class Registry:
    # The registry is the single adapter lookup table for configured targets. It keeps the
    # rest of the app target-aware without scattering platform-specific branching everywhere.
    def __init__(self, targets):
        self.targets = {}
        for raw_target in targets.get("targets", []):
            target = Target(**raw_target)
            adapter = self._build_adapter(target)
            if adapter:
                self.targets[target.id] = adapter

    def _build_adapter(self, target: Target):
        if target.kind == "flowise":
            return FlowiseAdapter(target)
        if target.kind == "langflow":
            return LangflowAdapter(target)
        if target.kind == "custom_api":
            return CustomAPIAdapter(target)
        if target.kind == "webarena" and WebArenaAdapter is not None:
            return WebArenaAdapter(target)
        return None

    def list_targets(self):
        targets = {}
        for key, adapter in self.targets.items():
            status = adapter.readiness()
            adapter.target.last_status = status
            spec = effective_target_spec(adapter.target)
            targets[key] = {
                "id": adapter.target.id,
                "name": adapter.target.name,
                "kind": adapter.target.kind,
                "platform": platform_label_for(adapter.target),
                "description": adapter.target.description,
                "enabled": adapter.target.enabled,
                "target_source": adapter.target.target_source,
                "profile": adapter.target.profile.model_dump(),
                "target_spec": spec.model_dump(),
                "available_modes": available_modes_for_target(adapter.target),
                "status": status.model_dump(),
            }
        return targets

    def get(self, target_id):
        return self.targets[target_id]


def build_registry(targets):
    return Registry(targets)
