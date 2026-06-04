import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.adapters.base import BaseAdapter, TargetExecutionError
from app.core.models import TargetStatus


# LangflowAdapter handles flows that may emit multiple output stages. It is responsible
# for deterministic output selection, JSON extraction, and schema-aware parse failures.
class LangflowAdapter(BaseAdapter):
    def required_settings(self):
        return ("base_url", "flow_id")

    def endpoint_url(self):
        base_url = self.target.settings.get("base_url", "").rstrip("/")
        flow_id = self.target.settings.get("flow_id", "")
        if not base_url or not flow_id:
            return None
        return f"{base_url}/api/v1/run/{flow_id}"

    # Langflow can succeed at the HTTP level while still returning the wrong stage or an
    # unusable wrapper payload. Execution therefore includes selection, JSON parsing, and
    # analysis-schema validation before the run is treated as trustworthy.
    def execute(self, prompt: str):
        settings = self.target.settings
        url = self.endpoint_url()
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        key_env = settings.get("api_key_env")
        if key_env and os.getenv(key_env):
            headers["x-api-key"] = os.getenv(key_env)
        payload = {
            "input_value": self._format_input_value(prompt),
            "input_type": settings.get("input_type", "chat"),
            "output_type": settings.get("output_type", "chat"),
            "session_id": settings.get("session_id", "crashlab-session"),
        }

        try:
            data, attempt_count = self.request_json("POST", url, headers=headers, json_body=payload)
        except TargetExecutionError as exc:
            if exc.kind == "provider_quota_exceeded":
                detail = "Langflow reached its upstream model quota. Update the Langflow model credentials, provider, or billing before rerunning."
                self.set_last_status(TargetStatus.provider_quota_exceeded(detail))
            raise
        selection = self._select_output(data)
        meta = {
            "request_summary": {
                "url": url,
                "payload_keys": list(payload.keys()),
                "api_key_present": bool(key_env and os.getenv(key_env)),
                "read_timeout_seconds": self.read_timeout_seconds(),
                "timeout_retry_count": self.timeout_retry_count(),
                "attempt_count": attempt_count,
            },
            "response_summary": self.summarize_payload(data),
            "langflow": {
                "selected_output": selection["meta"],
                "parsed_json": selection.get("parsed_json") or {},
                "candidate_count": selection["meta"].get("candidate_count", 0),
                "selected_path": selection["meta"].get("selected_path", {}),
                "selection_ambiguous": selection["meta"].get("ambiguous", False),
            },
        }

        if selection.get("error"):
            detail = selection["error"]
            status = TargetStatus.response_parse_failed(detail)
            self.set_last_status(status)
            return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": detail}

        parsed_json = selection.get("parsed_json")
        rendered_text = self._render_output_text(selection.get("value"), parsed_json)
        if not rendered_text:
            detail = "Langflow returned JSON, but CrashLab could not render the selected analysis output."
            status = TargetStatus.response_parse_failed(detail)
            self.set_last_status(status)
            return {"ok": False, "text": "", "meta": meta, "error_type": status.code, "error": detail}

        self.set_last_status(TargetStatus.ready("Langflow call and output selection succeeded."))
        return {"ok": True, "text": rendered_text, "meta": meta}

    # Langflow can return multiple output stages. CrashLab picks the configured final
    # output path first and only falls back when selection would still be trustworthy.
    def _select_output(self, payload: Any) -> Dict[str, Any]:
        candidates = self._collect_output_candidates(payload)
        selector_mode, selectors = self._active_selectors()
        explicit = selector_mode != "score_only"
        matches = [candidate for candidate in candidates if self._matches_selectors(candidate, selectors)] if explicit else list(candidates)

        meta = {
            "reason": "unresolved",
            "ambiguous": False,
            "candidate_count": len(candidates),
            "matched_candidate_count": len(matches),
            "selector_mode": selector_mode,
            "selectors": selectors,
            "chosen_descriptor": {},
            "selected_path": {},
            "candidate_descriptors": [candidate["descriptor"] for candidate in candidates[:12]],
        }

        if not candidates:
            meta["reason"] = "no_candidate"
            return {"value": None, "parsed_json": None, "meta": meta, "error": "Langflow returned no extractable output candidates."}

        if explicit and not matches:
            meta["reason"] = "configured_selector_no_match"
            return {
                "value": None,
                "parsed_json": None,
                "meta": meta,
                "error": "Configured Langflow output selectors did not match any returned output. Update output_component or the preferred output path settings.",
            }

        ranked = sorted(matches, key=self._candidate_sort_key, reverse=True)
        if not ranked:
            meta["reason"] = "no_ranked_candidate"
            return {"value": None, "parsed_json": None, "meta": meta, "error": "Langflow returned candidates, but none could be ranked as usable analysis output."}

        top_score = ranked[0]["score"]
        top_candidates = [candidate for candidate in ranked if candidate["score"] == top_score]
        distinct_top = self._distinct_top_candidates(top_candidates)
        if explicit and len(distinct_top) > 1:
            meta["reason"] = "configured_selector_ambiguous"
            meta["ambiguous"] = True
            return {
                "value": None,
                "parsed_json": None,
                "meta": meta,
                "error": "Configured Langflow selectors still match multiple equally strong outputs. Narrow the selection with a more specific output_component or preferred output path.",
            }
        if not explicit:
            if top_score < 5:
                meta["reason"] = "weak_best_candidate"
                meta["ambiguous"] = True
                return {
                    "value": None,
                    "parsed_json": None,
                    "meta": meta,
                    "error": "Langflow returned multiple weak or wrapper-like outputs. Configure a deterministic output path before trusting the run.",
                }
            if len(distinct_top) > 1:
                meta["reason"] = "ambiguous_best_candidate"
                meta["ambiguous"] = True
                return {
                    "value": None,
                    "parsed_json": None,
                    "meta": meta,
                    "error": "Langflow returned multiple equally strong output candidates. Configure output_component or preferred output path settings.",
                }

        chosen = ranked[0]
        parsed_json = chosen.get("parsed_json") or self._parse_candidate_json(chosen.get("value"))
        if selector_mode == "component":
            meta["reason"] = "configured_component"
        elif selector_mode == "path":
            meta["reason"] = "configured_path"
        else:
            meta["reason"] = "best_scored_candidate"
        meta["chosen_descriptor"] = chosen["descriptor"]
        meta["selected_path"] = {
            "output_index": chosen["descriptor"].get("output_index"),
            "nested_index": chosen["descriptor"].get("nested_index"),
            "result_key": chosen["descriptor"].get("result_key"),
            "field_path": chosen["descriptor"].get("field_path"),
            "component_label": chosen["descriptor"].get("component_label"),
            "component_id": chosen["descriptor"].get("component_id"),
        }
        meta["chosen_score"] = chosen["score"]

        if self.target.profile.family == "analysis_pipeline" and not self._matches_expected_schema(parsed_json):
            meta["reason"] = f"{meta['reason']}:schema_mismatch"
            return {
                "value": chosen.get("value"),
                "parsed_json": parsed_json,
                "meta": meta,
                "error": "Selected Langflow output did not match the expected analysis schema. Tighten the final Langflow output or update the configured output path.",
            }
        fallback_reason = self._analysis_fallback_reason(parsed_json)
        if fallback_reason:
            meta["reason"] = f"{meta['reason']}:fallback_output"
            return {
                "value": chosen.get("value"),
                "parsed_json": parsed_json,
                "meta": meta,
                "error": fallback_reason,
            }

        return {"value": chosen.get("value"), "parsed_json": parsed_json, "meta": meta, "error": None}

    def _collect_output_candidates(self, payload: Any) -> List[Dict[str, Any]]:
        outputs = payload.get("outputs", []) if isinstance(payload, dict) else []
        candidates: List[Dict[str, Any]] = []
        seen = set()
        for output_index, output in enumerate(outputs):
            output_meta = self._component_meta(output)
            nested_outputs = output.get("outputs", []) if isinstance(output, dict) else []
            for nested_index, nested in enumerate(nested_outputs):
                nested_meta = self._component_meta(nested)
                results = nested.get("results", {}) if isinstance(nested, dict) else {}
                for key, value in results.items():
                    variants = self._extract_candidate_variants(value)
                    for field_path, variant in variants:
                        parsed_json = self._parse_candidate_json(variant)
                        descriptor = {
                            "output_index": output_index,
                            "nested_index": nested_index,
                            "result_key": key,
                            "field_path": field_path,
                            "component_label": nested_meta.get("component_label") or output_meta.get("component_label"),
                            "component_id": nested_meta.get("component_id") or output_meta.get("component_id"),
                            "type": type(variant).__name__,
                        }
                        dedupe_key = json.dumps(descriptor, sort_keys=True, default=str)
                        if dedupe_key in seen:
                            continue
                        seen.add(dedupe_key)
                        candidates.append(
                            {
                                "value": variant,
                                "parsed_json": parsed_json,
                                "score": self._score_candidate(variant, parsed_json),
                                "descriptor": descriptor,
                            }
                        )
        return candidates

    def _component_meta(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        candidates = [
            value.get("component_display_name"),
            value.get("display_name"),
            value.get("name"),
            value.get("component"),
        ]
        component_label = next((item for item in candidates if isinstance(item, str) and item.strip()), None)
        component_id = value.get("component_id") or value.get("id")
        return {"component_label": component_label, "component_id": component_id}

    def _extract_candidate_variants(self, value: Any) -> List[Tuple[str, Any]]:
        variants: List[Tuple[str, Any]] = [("", value)]
        for path in ("text", "message", "content", "output", "response"):
            extracted = self._get_path(value, path)
            if extracted is not None:
                variants.append((path, extracted))
        for path in ("data.text", "data.message", "data.content"):
            extracted = self._get_path(value, path)
            if extracted is not None:
                variants.append((path, extracted))
        artifacts = self._get_path(value, "artifacts")
        if isinstance(artifacts, list):
            for index, artifact in enumerate(artifacts[:6]):
                variants.append((f"artifacts[{index}]", artifact))
                for suffix in ("text", "message", "content", "data"):
                    extracted = self._get_path(artifact, suffix)
                    if extracted is not None:
                        variants.append((f"artifacts[{index}].{suffix}", extracted))
        deduped: List[Tuple[str, Any]] = []
        seen = set()
        for field_path, variant in variants:
            marker = f"{field_path}:{self._stable_preview(variant)}"
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append((field_path, variant))
        return deduped

    def _get_path(self, value: Any, dotted_path: str):
        current = value
        for piece in dotted_path.split("."):
            if not isinstance(current, dict) or piece not in current:
                return None
            current = current[piece]
        return current

    def _score_candidate(self, value: Any, parsed_json: Optional[Dict[str, Any]]) -> int:
        score = 0
        if parsed_json:
            keys = {key.lower() for key in parsed_json.keys()}
            if "sentiment" in keys:
                score += 6
            if keys & {"summary", "analysis"}:
                score += 5
            if keys & {"action_item", "recommendation", "action_recommendation"}:
                score += 5
            if keys & {"confidence", "evidence_note"}:
                score += 2
            if keys & {"message_sentiment", "message_category"} and not keys & {"summary", "analysis", "action_item", "recommendation"}:
                score -= 6
        if isinstance(value, dict):
            keys = {key.lower() for key in value.keys()}
            if keys & {"text", "message", "data"}:
                score += 1
        elif isinstance(value, str):
            lowered = value.lower()
            if "no messages were provided" in lowered:
                score -= 7
            if lowered.strip().startswith("{") or "```json" in lowered:
                score += 2
        return score

    def _parse_candidate_json(self, value: Any) -> Optional[Dict[str, Any]]:
        if isinstance(value, dict):
            if self._matches_expected_schema(value):
                return value
            for path in ("text", "message", "content", "output", "response", "data.text", "data.message", "data.content"):
                nested = self._get_path(value, path)
                parsed = self._parse_candidate_json(nested)
                if parsed:
                    return parsed
            artifacts = self._get_path(value, "artifacts")
            if isinstance(artifacts, list):
                for artifact in artifacts[:6]:
                    parsed = self._parse_candidate_json(artifact)
                    if parsed:
                        return parsed
            return None
        if isinstance(value, list):
            for item in value[:6]:
                parsed = self._parse_candidate_json(item)
                if parsed:
                    return parsed
            return None
        if not isinstance(value, str):
            return None
        stripped = value.strip()
        if not stripped:
            return None
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
        if match:
            stripped = match.group(1).strip()
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def _matches_expected_schema(self, parsed_json: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(parsed_json, dict):
            return False
        keys = {key.lower() for key in parsed_json.keys()}
        has_sentiment = "sentiment" in keys
        has_summary = "summary" in keys or "analysis" in keys
        has_action = bool(keys & {"action_item", "recommendation", "action_recommendation"})
        return has_sentiment and has_summary and has_action

    def _analysis_fallback_reason(self, parsed_json: Optional[Dict[str, Any]]) -> Optional[str]:
        if not isinstance(parsed_json, dict):
            return None
        summary = str(parsed_json.get("summary") or parsed_json.get("analysis") or "").lower()
        action_item = str(parsed_json.get("action_item") or parsed_json.get("recommendation") or "").lower()
        combined = f"{summary} {action_item}"
        fallback_tokens = [
            "didn’t receive any messages",
            "didn't receive any messages",
            "no langflow community messages were provided",
            "messages were provided",
            "message list",
            "provide the messages",
            "missing fields",
            "input appears empty",
            "validation fails",
            "schema check",
            "api boundary",
        ]
        if any(token in combined for token in fallback_tokens):
            return "Langflow selected its fallback validation output instead of a grounded feedback analysis. The flow is reachable, but it is still not consuming the provided input correctly."
        return None

    def _format_input_value(self, prompt: str) -> str:
        mode = str(self.target.settings.get("input_format", "plain_text")).strip().lower()
        if mode != "community_feedback_record":
            return prompt
        payload = {
            "start_date": self.target.settings.get("default_start_date", "2026-04-01"),
            "end_date": self.target.settings.get("default_end_date", "2026-04-16"),
            "messages": [
                {
                    "message_id": "crashlab-case",
                    "created_at": self.target.settings.get("default_message_timestamp", "2026-04-16T00:00:00Z"),
                    "message_content": prompt,
                }
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    def _active_selectors(self) -> Tuple[str, Dict[str, Any]]:
        output_component = self.target.settings.get("output_component")
        if isinstance(output_component, str) and output_component.strip():
            return "component", {"output_component": output_component.strip()}

        path_selectors = {
            "preferred_output_index": self.target.settings.get("preferred_output_index"),
            "preferred_nested_index": self.target.settings.get("preferred_nested_index"),
            "preferred_result_key": self.target.settings.get("preferred_result_key"),
        }
        if any(value not in (None, "") for value in path_selectors.values()):
            return "path", path_selectors
        return "score_only", {}

    def _matches_selectors(self, candidate: Dict[str, Any], selectors: Dict[str, Any]) -> bool:
        descriptor = candidate.get("descriptor", {})
        output_component = selectors.get("output_component")
        if output_component not in (None, ""):
            label = str(descriptor.get("component_label") or "").lower()
            component_id = str(descriptor.get("component_id") or "").lower()
            needle = str(output_component).strip().lower()
            if needle not in label and needle not in component_id:
                return False
            return True
        output_index = selectors.get("preferred_output_index")
        nested_index = selectors.get("preferred_nested_index")
        result_key = str(selectors.get("preferred_result_key") or "").strip()
        if output_index in (None, "") and nested_index in (None, "") and not result_key:
            return True
        if output_index not in (None, ""):
            try:
                if descriptor.get("output_index") != int(output_index):
                    return False
            except (TypeError, ValueError):
                return False
        if nested_index not in (None, ""):
            try:
                if descriptor.get("nested_index") != int(nested_index):
                    return False
            except (TypeError, ValueError):
                return False
        if result_key:
            full_key = descriptor.get("result_key") or ""
            if descriptor.get("field_path"):
                full_key = f"{full_key}.{descriptor['field_path']}"
            if result_key != full_key:
                return False
        return True

    def _render_output_text(self, selected_output: Any, parsed_json: Optional[Dict[str, Any]]) -> str:
        if parsed_json:
            return json.dumps(parsed_json, indent=2, ensure_ascii=True)
        if isinstance(selected_output, dict):
            return json.dumps(selected_output, indent=2, ensure_ascii=True)
        if isinstance(selected_output, str):
            return selected_output.strip()
        return ""

    def _stable_preview(self, value: Any) -> str:
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, sort_keys=True, default=str)
        else:
            rendered = str(value)
        return rendered[:240]

    def _candidate_sort_key(self, candidate: Dict[str, Any]):
        descriptor = candidate.get("descriptor", {})
        field_path = descriptor.get("field_path") or ""
        path_rank = 0
        if field_path == "text":
            path_rank = 3
        elif field_path == "data.text":
            path_rank = 2
        elif field_path:
            path_rank = 1
        return (candidate.get("score", 0), path_rank)

    def _distinct_top_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        distinct: List[Dict[str, Any]] = []
        seen = set()
        for candidate in candidates:
            marker_source = candidate.get("parsed_json") if candidate.get("parsed_json") else candidate.get("value")
            marker = self._stable_preview(marker_source)
            if marker in seen:
                continue
            seen.add(marker)
            distinct.append(candidate)
        return distinct
