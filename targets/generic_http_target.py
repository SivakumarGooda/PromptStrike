from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import requests

from utils.target_parser import render_request_parts


@dataclass
class TargetResponse:
    prompt: str
    llm_output: str
    breakthrough_detected: bool
    detected_issues: List[str]
    system_prompt_hint: str
    timestamp: Optional[str]
    input_length: Optional[int]
    status_code: int
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GenericHTTPTarget:
    def __init__(self, config: Dict[str, Any], timeout: int = 30):
        self.config = config
        self.timeout = timeout

        scheme = "https" if config.get("use_tls", True) else "http"
        host = config["host"]
        endpoint = config["endpoint"]
        self.url = f"{scheme}://{host}{endpoint}"

        self.method = config.get("method", "POST").upper()

    def _extract_response_field(self, data: Dict[str, Any]) -> str:
        field = self.config.get("response_field", "llm_output")

        if "." not in field:
            return str(data.get(field, ""))

        current: Any = data
        for part in field.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if idx >= len(current):
                    return ""
                current = current[idx]
            else:
                return ""

        return "" if current is None else str(current)

    def send_prompt(self, prompt: str) -> TargetResponse:
        rendered = render_request_parts(self.config, prompt)
        body_mode = rendered["body_mode"]
        headers = rendered["headers"]
        payload = rendered["payload"]

        request_kwargs: Dict[str, Any] = {
            "method": self.method,
            "url": self.url,
            "headers": headers,
            "timeout": self.timeout,
        }

        if body_mode == "json":
            request_kwargs["json"] = payload
        elif body_mode in {"form", "raw", "multipart"}:
            request_kwargs["data"] = payload

        response = requests.request(**request_kwargs)
        response.raise_for_status()

        try:
            data = response.json()
            llm_output = self._extract_response_field(data)
        except ValueError:
            data = {"raw_text": response.text}
            llm_output = response.text

        return TargetResponse(
            prompt=prompt,
            llm_output=llm_output,
            breakthrough_detected=bool(data.get("breakthrough_detected", False)),
            detected_issues=list(data.get("detected_issues", [])),
            system_prompt_hint=str(data.get("system_prompt_hint", "")),
            timestamp=data.get("timestamp"),
            input_length=data.get("input_length"),
            status_code=response.status_code,
            raw=data,
        )