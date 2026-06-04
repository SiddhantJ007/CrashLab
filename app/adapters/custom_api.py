import json
import os

from app.adapters.base import BaseAdapter
from app.core.models import TargetStatus


class CustomAPIAdapter(BaseAdapter):
    def required_settings(self):
        return ("base_url", "endpoint_path")

    def probe_url(self):
        return self.target.settings.get("base_url", "").rstrip("/") or None

    def endpoint_url(self):
        base_url = self.target.settings.get("base_url", "").rstrip("/")
        endpoint_path = self.target.settings.get("endpoint_path", "").strip()
        if not base_url or not endpoint_path:
            return None
        return f"{base_url}/{endpoint_path.lstrip('/')}"

    # Custom API targets are intentionally simple: CrashLab sends a prompt envelope and then
    # uses the shared text extraction logic to look for a usable response field.
    def execute(self, prompt: str):
        url = self.endpoint_url()
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        key_env = self.target.settings.get("api_key_env")
        if key_env and os.getenv(key_env):
            headers["Authorization"] = f"Bearer {os.getenv(key_env)}"
        payload = {
            "input": prompt,
            "prompt": prompt,
            "message": prompt,
            "query": prompt,
        }
        data, attempt_count = self.request_json("POST", url, headers=headers, json_body=payload)
        candidates = self.extract_text_candidates(data)
        text = candidates[0] if candidates else ""
        if not text and isinstance(data, dict) and self.target.target_spec.expected_output_style in {"json", "structured_answer"}:
            text = json.dumps(data, indent=2)
        meta = {
            "request_summary": {
                "url": url,
                "payload_keys": list(payload.keys()),
                "api_key_present": bool(key_env and os.getenv(key_env)),
                "attempt_count": attempt_count,
            },
            "response_summary": self.summarize_payload(data),
            "text_candidates": candidates[:5],
        }
        if not text:
            status = TargetStatus.response_parse_failed("Custom API target returned JSON, but CrashLab could not extract a text-like response field.")
            self.set_last_status(status)
            return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": status.detail}
        self.set_last_status(TargetStatus.ready("Custom API call and response parsing succeeded."))
        return {"ok": True, "text": str(text), "meta": meta}
