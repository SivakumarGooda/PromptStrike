from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any, Dict, Optional

import requests


class TargetSender:
    def __init__(self, config: Dict[str, Any], timeout: int | None = None) -> None:
        self.config = config
        self.timeout = timeout or int(config.get("timeout", 30))

    def send_prompt(self, prompt: str) -> Dict[str, Any]:
        method = str(self.config.get("method", "POST")).upper()
        url = str(self.config["url"])
        headers = deepcopy(self.config.get("headers", {}))
        body_template = deepcopy(self.config.get("body"))
        prompt_field = str(self.config.get("prompt_field", "prompt"))
        response_field = self.config.get("response_field")
        body_mode = str(self.config.get("body_mode", "json"))
        multipart_boundary = self.config.get("multipart_boundary")

        started = time.time()

        try:
            request_kwargs = {
                "method": method,
                "url": url,
                "headers": headers,
                "timeout": self.timeout,
            }

            request_body_for_log: Any = None

            if body_mode == "json":
                payload = self._inject_prompt(body_template, prompt_field, prompt)
                request_kwargs["json"] = payload
                request_body_for_log = payload

            elif body_mode == "form":
                payload = self._inject_prompt(body_template, prompt_field, prompt)
                request_kwargs["data"] = payload
                request_body_for_log = payload

            elif body_mode == "raw":
                payload = self._replace_raw_prompt(body_template, prompt)
                request_kwargs["data"] = payload
                request_body_for_log = payload

            elif body_mode == "multipart":
                payload_fields = self._inject_prompt(body_template, prompt_field, prompt)
                raw_body = self._encode_multipart_fields(payload_fields, multipart_boundary)
                request_kwargs["data"] = raw_body
                request_body_for_log = raw_body

                if multipart_boundary:
                    ct_key = next(
                        (k for k in headers if k.lower() == "content-type"),
                        "Content-Type",
                    )
                    headers[ct_key] = f"multipart/form-data; boundary={multipart_boundary}"

            else:
                payload = self._inject_prompt(body_template, prompt_field, prompt)
                request_kwargs["json"] = payload
                request_body_for_log = payload

            response = requests.request(**request_kwargs)
            latency_ms = int((time.time() - started) * 1000)

        except requests.RequestException as exc:
            return {
                "status_code": 0,
                "response_text": f"REQUEST_ERROR: {exc}",
                "raw_response_text": "",
                "response_json": None,
                "response_headers": {},
                "request": {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "body": None,
                },
                "latency_ms": 0,
                "error": str(exc),
            }

        raw_text = response.text

        parsed_json: Optional[Dict[str, Any] | list[Any]] = None
        try:
            parsed_json = response.json()
        except ValueError:
            parsed_json = None

        response_text = self._extract_response_text(
            raw_text=raw_text,
            parsed_json=parsed_json,
            response_field=response_field,
        )

        return {
            "status_code": response.status_code,
            "response_text": response_text,
            "raw_response_text": raw_text,
            "response_json": parsed_json,
            "response_headers": dict(response.headers),
            "request": {
                "method": method,
                "url": url,
                "headers": headers,
                "body": request_body_for_log,
            },
            "latency_ms": latency_ms,
            "error": None,
        }

    def _inject_prompt(self, body: Any, prompt_field: str, prompt: str) -> Any:
        result = deepcopy(body)

        if isinstance(result, dict):
            if "." not in prompt_field:
                result[prompt_field] = prompt
                return result

            parts = prompt_field.split(".")
            current = result

            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = prompt
            return result

        return result

    def _replace_raw_prompt(self, body_template: Any, prompt: str) -> str:
        if body_template is None:
            return prompt
        return str(body_template).replace("{PROMPT}", prompt)

    def _extract_response_text(
        self,
        raw_text: str,
        parsed_json: Any,
        response_field: Any,
    ) -> str:
        if response_field and parsed_json is not None:
            value = self._get_nested_value(parsed_json, str(response_field))
            if value is not None:
                if isinstance(value, str):
                    return value
                return json.dumps(value, ensure_ascii=False, indent=2)

        if isinstance(parsed_json, dict):
            for candidate in ["answer", "response", "output", "message", "content", "result", "text", "llm_output"]:
                if candidate in parsed_json:
                    value = parsed_json[candidate]
                    if isinstance(value, str):
                        return value
                    return json.dumps(value, ensure_ascii=False, indent=2)

        return raw_text

    def _get_nested_value(self, data: Any, path: str) -> Any:
        current = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _encode_multipart_fields(self, fields: Dict[str, Any], boundary: str | None) -> str:
        if not boundary:
            raise ValueError("multipart_boundary is required for multipart body mode")

        lines: list[str] = []

        for key, value in fields.items():
            lines.append(f"--{boundary}")
            lines.append(f'Content-Disposition: form-data; name="{key}"')
            lines.append("")
            lines.append("" if value is None else str(value))

        lines.append(f"--{boundary}--")
        lines.append("")
        return "\r\n".join(lines)