import os
from urllib.parse import urlsplit

from app.adapters.base import BaseAdapter
from app.core.models import TargetStatus


# FlowiseAdapter executes the Prediction API against a configured cloud or self-hosted
# flow and extracts both response text and observable execution metadata for reporting.
class FlowiseAdapter(BaseAdapter):
    def required_settings(self):
        base_url = str(self.setting("base_url", "") or "").strip()
        if "/api/v1/prediction/" in base_url:
            return ("base_url",)
        return ("base_url", "flow_id")

    def _raw_base_url(self) -> str:
        return str(self.setting("base_url", "") or "").strip().rstrip("/")

    def _normalized_prediction_url(self):
        base_url = self._raw_base_url()
        flow_id = str(self.setting("flow_id", "") or "").strip()
        if not base_url:
            return None
        if "/api/v1/prediction/" in base_url:
            return base_url
        if base_url.endswith("/api/v1/prediction") and flow_id:
            return f"{base_url}/{flow_id}"
        if not flow_id:
            return None
        return f"{base_url}/api/v1/prediction/{flow_id}"

    def probe_url(self):
        prediction_url = self._normalized_prediction_url()
        if not prediction_url:
            return None
        if "/api/v1/prediction/" not in prediction_url:
            return prediction_url
        parsed = urlsplit(prediction_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def endpoint_url(self):
        return self._normalized_prediction_url()

    def _summarize_agent_flow(self, executed_data):
        if not isinstance(executed_data, list):
            return {"step_count": 0, "node_labels": [], "tool_like_steps": 0}

        node_labels = []
        tool_like_steps = 0
        status_counts = {}

        for item in executed_data:
            if not isinstance(item, dict):
                continue
            label = item.get("nodeLabel") or item.get("label") or item.get("name") or item.get("id")
            if label:
                node_labels.append(str(label))
            node_type = str(item.get("nodeType") or item.get("type") or "").lower()
            if any(token in node_type for token in ("tool", "agent", "chain", "retriever")):
                tool_like_steps += 1
            status = item.get("status")
            if status:
                status_counts[str(status)] = status_counts.get(str(status), 0) + 1

        return {
            "step_count": len(executed_data),
            "node_labels": node_labels[:10],
            "tool_like_steps": tool_like_steps,
            "status_counts": status_counts,
        }

    # Flowise often returns both a primary text field and richer structured metadata. The
    # adapter prefers explicit text, then falls back to text-like candidates conservatively.
    def execute(self, prompt: str):
        s = self.target.settings
        url = self.endpoint_url()
        headers = {"Content-Type": "application/json"}
        token_env = s.get("auth_token_env")
        auth_header = s.get("auth_header", "Authorization")
        if token_env and os.getenv(token_env):
            token = os.getenv(token_env)
            headers[auth_header] = f"Bearer {token}" if auth_header.lower() == "authorization" else token
        payload = {"question": prompt, "streaming": False, "overrideConfig": {}, "history": []}
        data, attempt_count = self.request_json("POST", url, headers=headers, json_body=payload)
        text = str(data.get("text", "")).strip() if isinstance(data, dict) else ""
        candidates = self.extract_text_candidates(data)
        if not text and candidates:
            text = candidates[0]
        agent_flow_summary = self._summarize_agentFlow(data.get("agentFlowExecutedData")) if False else self._summarize_agent_flow(data.get("agentFlowExecutedData")) if isinstance(data, dict) else {"step_count": 0, "node_labels": [], "tool_like_steps": 0}
        meta = {
            "request_summary": {
                "url": url,
                "payload_keys": list(payload.keys()),
                "auth_header": auth_header,
                "auth_present": bool(token_env and os.getenv(token_env)),
                "read_timeout_seconds": self.read_timeout_seconds(),
                "timeout_retry_count": self.timeout_retry_count(),
                "attempt_count": attempt_count,
            },
            "response_summary": self.summarize_payload(data),
            "flowise": {
                "question": data.get("question") if isinstance(data, dict) else None,
                "chat_id": data.get("chatId") if isinstance(data, dict) else None,
                "chat_message_id": data.get("chatMessageId") if isinstance(data, dict) else None,
                "execution_id": data.get("executionId") if isinstance(data, dict) else None,
                "session_id": data.get("sessionId") if isinstance(data, dict) else None,
                "agent_flow_summary": agent_flow_summary,
            },
            "text_candidates": candidates[:5],
        }
        if not text:
            status = TargetStatus.response_parse_failed("Flowise returned JSON, but no text-like field could be extracted.")
            self.set_last_status(status)
            return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": status.detail}

        self.set_last_status(TargetStatus.ready("Flowise call and response parsing succeeded."))
        return {"ok": True, "text": str(text), "meta": meta}
