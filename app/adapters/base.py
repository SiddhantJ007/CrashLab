import json
import os
from typing import Any, Dict, Iterable, List, Optional

import httpx

from app.core.models import Target, TargetStatus


class TargetExecutionError(RuntimeError):
    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail


# BaseAdapter centralizes readiness checks, timeout handling, runtime setting resolution,
# and response-field extraction so every platform adapter reports failures consistently.
class BaseAdapter:
    def __init__(self, target: Target):
        self.target = target
        self._last_status: Optional[TargetStatus] = None

    def required_settings(self) -> Iterable[str]:
        return ()

    def endpoint_url(self) -> Optional[str]:
        return None

    def probe_url(self) -> Optional[str]:
        return self.endpoint_url()

    # Bootstrap targets can keep live endpoints out of git by declaring base_url_env,
    # flow_id_env, or endpoint_path_env. Direct values still win when explicitly set.
    def setting(self, key: str, default: Any = None):
        value = self.target.settings.get(key)
        if value not in (None, ""):
            return value
        env_name = self.target.settings.get(f"{key}_env")
        if isinstance(env_name, str) and env_name.strip():
            env_value = os.getenv(env_name.strip())
            if env_value not in (None, ""):
                return env_value
        return default

    def missing_settings(self) -> List[str]:
        missing = []
        for key in self.required_settings():
            value = self.setting(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(key)
        return missing

    def missing_settings_detail(self, missing: List[str]) -> str:
        labels = []
        for key in missing:
            env_name = self.target.settings.get(f"{key}_env")
            if isinstance(env_name, str) and env_name.strip():
                labels.append(f"{key} (set {env_name.strip()})")
            else:
                labels.append(key)
        return f"Missing required settings: {', '.join(labels)}"

    def readiness(self) -> TargetStatus:
        if not self.target.enabled:
            status = TargetStatus.disabled()
            self._last_status = status
            return status

        missing = self.missing_settings()
        if missing:
            status = TargetStatus.missing_config(self.missing_settings_detail(missing))
            self._last_status = status
            return status

        existing = self.get_last_status()
        if existing and existing.code in {"response_parse_failed", "provider_quota_exceeded"}:
            return existing

        url = self.probe_url()
        if not url:
            status = TargetStatus.ready("No reachability probe defined.")
            self._last_status = status
            return status

        try:
            with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                response = client.get(url)
            status = TargetStatus.ready(f"Endpoint reachable ({response.status_code}).")
        except Exception as exc:
            status = TargetStatus.unreachable(str(exc))

        self._last_status = status
        return status

    def set_last_status(self, status: TargetStatus):
        self._last_status = status
        self.target.last_status = status

    def get_last_status(self) -> Optional[TargetStatus]:
        return self._last_status or self.target.last_status

    def summarize_payload(self, payload: Any, max_chars: int = 280) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"type": type(payload).__name__}
        if isinstance(payload, dict):
            summary["keys"] = list(payload.keys())[:20]
        elif isinstance(payload, list):
            summary["length"] = len(payload)
        rendered = json.dumps(payload, default=str) if isinstance(payload, (dict, list)) else str(payload)
        if len(rendered) > max_chars:
            rendered = f"{rendered[:max_chars]}..."
        summary["preview"] = rendered
        return summary

    # Response parsing stays conservative: if we cannot extract a stable text-like field,
    # the caller should surface a parse failure instead of pretending the run succeeded.
    def extract_text_candidates(self, payload: Any) -> List[str]:
        candidates: List[str] = []

        def walk(value: Any):
            if value is None:
                return
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    candidates.append(cleaned)
                return
            if isinstance(value, dict):
                preferred_keys = (
                    "text",
                    "message",
                    "output",
                    "output_text",
                    "answer",
                    "content",
                    "response",
                )
                for key in preferred_keys:
                    if key in value:
                        walk(value[key])
                for nested in value.values():
                    walk(nested)
                return
            if isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)
        deduped: List[str] = []
        seen = set()
        for candidate in candidates:
            if candidate not in seen:
                deduped.append(candidate)
                seen.add(candidate)
        return deduped

    def execute(self, prompt: str):
        raise NotImplementedError

    def connect_timeout_seconds(self) -> float:
        return float(self.setting("connect_timeout_seconds", 5))

    def read_timeout_seconds(self) -> float:
        return float(self.setting("read_timeout_seconds", 60))

    def write_timeout_seconds(self) -> float:
        return float(self.setting("write_timeout_seconds", 30))

    def pool_timeout_seconds(self) -> float:
        return float(self.setting("pool_timeout_seconds", 5))

    def timeout_retry_count(self) -> int:
        return int(self.setting("timeout_retry_count", 0))

    def http_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout_seconds(),
            read=self.read_timeout_seconds(),
            write=self.write_timeout_seconds(),
            pool=self.pool_timeout_seconds(),
        )

    # All adapters use the same HTTP wrapper so execution failures, provider quota errors,
    # invalid JSON responses, and retryable timeout types are normalized before the runner
    # assigns trust labels.
    def request_json(self, method: str, url: str, *, headers: Optional[Dict[str, str]] = None, json_body: Optional[Dict[str, Any]] = None):
        attempts = self.timeout_retry_count() + 1
        last_timeout_kind = "timeout"
        last_timeout_detail = ""
        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(timeout=self.http_timeout(), follow_redirects=True) as client:
                    response = client.request(method, url, headers=headers, json=json_body)
                response.raise_for_status()
                try:
                    return response.json(), attempt
                except ValueError:
                    preview = response.text[:300].replace("\n", " ").strip()
                    raise TargetExecutionError(
                        "invalid_json_response",
                        f"Target returned a non-JSON response. URL: {url}. Preview: {preview or '[empty response]'}",
                    )
            except httpx.ReadTimeout:
                last_timeout_kind = "timeout_read"
                last_timeout_detail = f"Read timeout after {self.read_timeout_seconds()}s"
            except httpx.ConnectTimeout:
                last_timeout_kind = "timeout_connect"
                last_timeout_detail = f"Connect timeout after {self.connect_timeout_seconds()}s"
            except httpx.TimeoutException:
                last_timeout_kind = "timeout"
                last_timeout_detail = "Request timed out"
            except httpx.HTTPStatusError as exc:
                detail = f"HTTP {exc.response.status_code}: {exc.response.text[:300]}"
                lowered = detail.lower()
                if any(token in lowered for token in ["quota", "insufficient_quota", "exceeded your current quota", "billing details"]):
                    raise TargetExecutionError("provider_quota_exceeded", detail)
                raise TargetExecutionError("http_error", detail)
            except httpx.HTTPError as exc:
                raise TargetExecutionError("network_error", str(exc))

            if attempt >= attempts:
                retry_note = f" after {attempts} attempts" if attempts > 1 else ""
                raise TargetExecutionError(last_timeout_kind, f"{last_timeout_detail}{retry_note}")

        raise TargetExecutionError("timeout", "Request timed out")
