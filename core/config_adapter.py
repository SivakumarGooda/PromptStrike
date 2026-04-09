from __future__ import annotations

from typing import Any, Dict


def adapt_config_to_sender(parser_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert target_parser config format into TargetSender config format.
    """

    scheme = "https" if parser_config.get("use_tls") else "http"
    url = f"{scheme}://{parser_config['host']}{parser_config['endpoint']}"

    return {
        "url": url,
        "method": parser_config.get("method", "POST"),
        "headers": parser_config.get("headers", {}),
        "body": parser_config.get("body_template"),
        "prompt_field": parser_config.get("prompt_param", "prompt"),
        "response_field": parser_config.get("response_field", "llm_output"),
        "body_mode": parser_config.get("body_mode", "json"),
        "timeout": parser_config.get("timeout", 30),
        "multipart_boundary": parser_config.get("multipart_boundary"),
    }