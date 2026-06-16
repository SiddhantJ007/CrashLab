import json
from typing import Any, Dict, List, Optional, Tuple

from app.adapters.base import BaseAdapter
from app.core.models import TargetStatus


# DifyAdapter executes a published Dify chat, agent, or workflow app over the public API.
# CrashLab treats the target as a black box and only accepts outputs it can extract, parse,
# and validate against the selected family and expected output style.
class DifyAdapter(BaseAdapter):
    def required_settings(self):
        return ("base_url", "endpoint_path", "api_key")

    def endpoint_url(self):
        base_url = str(self.setting("base_url", "") or "").rstrip("/")
        endpoint_path = str(self.setting("endpoint_path", "") or "").strip()
        if not base_url or not endpoint_path:
            return None
        if endpoint_path.startswith(("http://", "https://")):
            return endpoint_path
        normalized = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        return f"{base_url}{normalized}"

    def probe_url(self):
        base_url = str(self.setting("base_url", "") or "").rstrip("/")
        return base_url or self.endpoint_url()

    def execute(self, prompt: str):
        url = self.endpoint_url()
        api_key = str(self.setting("api_key", "") or "").strip()
        payload = {
            "inputs": self.setting("inputs", {}) or {},
            "query": prompt,
            "response_mode": self.setting("response_mode", "blocking"),
            "conversation_id": self.setting("conversation_id", ""),
            "user": self.setting("user", f"crashlab-{self.target.id}"),
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data, attempt_count = self.request_json("POST", url, headers=headers, json_body=payload)
        answer, parsed_json, selection_reason, candidate_count = self._select_output(data)
        meta = {
            "request_summary": {
                "url": url,
                "payload_keys": list(payload.keys()),
                "api_key_present": bool(api_key),
                "read_timeout_seconds": self.read_timeout_seconds(),
                "timeout_retry_count": self.timeout_retry_count(),
                "attempt_count": attempt_count,
            },
            "response_summary": self.summarize_payload(data),
            "dify": {
                "event": data.get("event") if isinstance(data, dict) else None,
                "task_id": data.get("task_id") if isinstance(data, dict) else None,
                "message_id": data.get("message_id") if isinstance(data, dict) else None,
                "conversation_id": data.get("conversation_id") if isinstance(data, dict) else None,
                "mode": data.get("mode") if isinstance(data, dict) else None,
                "answer_preview": (answer or "")[:280],
                "parsed_json": parsed_json or {},
                "metadata": data.get("metadata", {}) if isinstance(data, dict) else {},
                "selection_reason": selection_reason,
                "candidate_count": candidate_count,
            },
        }

        if not answer:
            detail = "Dify returned JSON, but CrashLab could not extract a usable final answer from the configured response payload."
            status = TargetStatus.response_parse_failed(detail)
            self.set_last_status(status)
            return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": detail}

        if self.expected_output_style() == "json" and not self.matches_expected_schema(parsed_json):
            detail = "Selected Dify output did not match the expected JSON schema for this target. Tighten the Dify prompt or align the target schema settings."
            status = TargetStatus.response_parse_failed(detail)
            self.set_last_status(status)
            return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": detail}

        if self.target.profile.family == "analysis_pipeline":
            fallback_reason = self._analysis_fallback_reason(parsed_json)
            if fallback_reason:
                status = TargetStatus.response_parse_failed(fallback_reason)
                self.set_last_status(status)
                return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": fallback_reason}

        rendered_text = self.render_expected_output(answer, parsed_json)
        if not rendered_text:
            detail = "Dify returned a response, but CrashLab could not render it into usable text."
            status = TargetStatus.response_parse_failed(detail)
            self.set_last_status(status)
            return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": detail}

        self.set_last_status(TargetStatus.ready("Dify call and output validation succeeded."))
        return {"ok": True, "text": rendered_text, "meta": meta}

    def _candidate_entries(self, payload: Any) -> List[Tuple[str, Any]]:
        entries: List[Tuple[str, Any]] = []

        def add(reason: str, value: Any):
            if value in (None, "", [], {}):
                return
            entries.append((reason, value))

        if isinstance(payload, dict):
            add("answer_field", payload.get("answer"))
            add("text", payload.get("text"))
            add("output_text", payload.get("output_text"))
            add("response", payload.get("response"))
            add("content", payload.get("content"))

            data = payload.get("data")
            if isinstance(data, dict):
                add("data.answer", data.get("answer"))
                outputs = data.get("outputs")
                if isinstance(outputs, dict):
                    for key in ("answer", "text", "output", "result", "message"):
                        add(f"data.outputs.{key}", outputs.get(key))
                    add("data.outputs", outputs)

            outputs = payload.get("outputs")
            if isinstance(outputs, dict):
                for key in ("answer", "text", "output", "result", "message"):
                    add(f"outputs.{key}", outputs.get(key))
                add("outputs", outputs)

            message = payload.get("message")
            if isinstance(message, dict):
                for key in ("text", "content", "answer", "message"):
                    add(f"message.{key}", message.get(key))
                artifacts = message.get("artifacts")
                if isinstance(artifacts, dict):
                    for key in ("text", "message", "answer", "output"):
                        add(f"message.artifacts.{key}", artifacts.get(key))
                    add("message.artifacts", artifacts)

            workflow_run = payload.get("workflow_run")
            if isinstance(workflow_run, dict):
                outputs = workflow_run.get("outputs")
                if isinstance(outputs, dict):
                    for key in ("answer", "text", "output", "result", "message"):
                        add(f"workflow_run.outputs.{key}", outputs.get(key))
                add("workflow_run.outputs", outputs)

        for index, candidate in enumerate(self.extract_text_candidates(payload)):
            add(f"text_candidate:{index}", candidate)

        deduped: List[Tuple[str, Any]] = []
        seen = set()
        for reason, value in entries:
            marker = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
            if marker in seen:
                continue
            deduped.append((reason, value))
            seen.add(marker)
        return deduped

    def _select_output(self, payload: Any):
        candidates = self._candidate_entries(payload)
        selected_text = ""
        selected_json: Optional[Dict[str, Any]] = None
        selected_reason = "none"
        fallback_text = ""
        fallback_json: Optional[Dict[str, Any]] = None
        fallback_reason = "none"

        expected_json = self.expected_output_style() == "json"
        family_json_keys = {"sentiment", "summary", "action_item", "confidence", "evidence_note"}

        for reason, raw_value in candidates:
            parsed_json = self.parse_json_text(raw_value)
            rendered = raw_value.strip() if isinstance(raw_value, str) else json.dumps(raw_value, ensure_ascii=False)
            if not fallback_text and rendered:
                fallback_text, fallback_json, fallback_reason = rendered, parsed_json, reason

            if expected_json and self.matches_expected_schema(parsed_json):
                return rendered, parsed_json, f"configured_schema:{reason}", len(candidates)

            if isinstance(parsed_json, dict) and family_json_keys.intersection(parsed_json.keys()):
                selected_text, selected_json, selected_reason = rendered, parsed_json, f"structured_json:{reason}"
                if not expected_json:
                    break

        if selected_text:
            return selected_text, selected_json, selected_reason, len(candidates)
        return fallback_text, fallback_json, fallback_reason, len(candidates)

    def _analysis_fallback_reason(self, parsed_json: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(parsed_json, dict):
            return None
        joined = " ".join(str(parsed_json.get(key, "")) for key in ("summary", "action_item", "evidence_note")).lower()
        fallback_markers = [
            "no messages were provided",
            "no message was provided",
            "no feedback was provided",
            "input was empty",
            "no source feedback",
        ]
        if any(marker in joined for marker in fallback_markers):
            return "Dify selected a fallback or empty-input answer instead of a grounded feedback analysis. The app is reachable, but it is still not consuming the provided input correctly."
        return None
