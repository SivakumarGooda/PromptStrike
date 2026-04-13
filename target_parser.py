from __future__ import annotations

import json
import re
import shlex
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urlencode, urlparse


DEFAULT_CONFIG_NAME = "app.config"
DEFAULT_CONFIG_PATH = Path("configs") / f"{DEFAULT_CONFIG_NAME}.json"

TARGET_DATASET_DIR = Path("datasets") / "targets" / "app"
TARGET_RULE_DISCLOSURE_PATH = TARGET_DATASET_DIR / "app_rule_disclosure.txt"
TARGET_PROMPT_INJECTION_PATH = TARGET_DATASET_DIR / "app_prompt_injection.txt"

BASE_DATASET_DIR = Path("datasets") / "base"
BASE_RULE_DISCLOSURE_PATH = BASE_DATASET_DIR / "base_rule_disclosure.txt"
BASE_PROMPT_INJECTION_PATH = BASE_DATASET_DIR / "base_prompt_injection.txt"

NOISY_HEADERS = {
    "accept",
    "accept-language",
    "accept-encoding",
    "connection",
    "origin",
    "referer",
    "sec-fetch-dest",
    "sec-fetch-mode",
    "sec-fetch-site",
    "sec-ch-ua",
    "sec-ch-ua-mobile",
    "sec-ch-ua-platform",
    "user-agent",
    "priority",
}


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def ask_yes_no(prompt: str, default: str = "n") -> bool:
    while True:
        value = ask(prompt, default).lower()
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("Please enter y or n.")


def ask_choice(prompt: str, valid_choices: List[str], default: str | None = None) -> str:
    valid_set = set(valid_choices)
    while True:
        value = ask(prompt, default)
        if value in valid_set:
            return value
        print(f"Invalid choice. Choose one of: {', '.join(valid_choices)}")


def choose_from_list(title: str, items: list[tuple[str, Any]]) -> str:
    print(title)
    for idx, (key, value) in enumerate(items, 1):
        print(f"  {idx}. {key} = {value}")

    while True:
        raw = input("Select field number: ").strip()
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(items):
                return items[choice - 1][0]
        print("Invalid choice. Try again.")


def prompt_multiline_input(prompt: str) -> str:
    print(prompt)
    print("Paste the full curl command.")
    print("Finish input with:")
    print("  - Ctrl+D (macOS/Linux)")
    print("  - Ctrl+Z then Enter (Windows)")

    lines: list[str] = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass

    return "\n".join(lines).strip()


def normalize_curl_text(curl_text: str) -> str:
    curl_text = curl_text.replace("\\\r\n", " ")
    curl_text = curl_text.replace("\\\n", " ")
    curl_text = curl_text.replace("$'", "'")
    return " ".join(curl_text.split())


def sanitize_json_text(text: str) -> str:
    result: list[str] = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            result.append(ch)
            escape = False
            continue

        if ch == "\\":
            result.append(ch)
            escape = True
            continue

        if ch == '"':
            result.append(ch)
            in_string = not in_string
            continue

        if in_string:
            if ch == "\n":
                result.append("\\n")
                continue
            if ch == "\r":
                result.append("\\r")
                continue
            if ch == "\t":
                result.append("\\t")
                continue

        result.append(ch)

    return "".join(result)


def normalize_body_raw(body_raw: str | None) -> str | None:
    if body_raw is None:
        return None

    text = body_raw.strip()

    if text.startswith("$'") and text.endswith("'"):
        text = text[2:-1]
    elif text.startswith("'") and text.endswith("'"):
        text = text[1:-1]
    elif text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    try:
        text = bytes(text, "utf-8").decode("unicode_escape")
    except Exception:
        pass

    return text


def clean_headers(headers: Dict[str, str]) -> Dict[str, str]:
    cleaned: Dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() not in NOISY_HEADERS:
            cleaned[k] = v
    return cleaned


def parse_curl(curl_text: str) -> Dict[str, Any]:
    curl_text = normalize_curl_text(curl_text)
    parts = shlex.split(curl_text)

    if not parts or parts[0] != "curl":
        raise ValueError("Input does not look like a curl command.")

    method = "GET"
    url = None
    headers: Dict[str, str] = {}
    body_raw = None

    i = 1
    while i < len(parts):
        part = parts[i]

        if part in ("-X", "--request"):
            i += 1
            method = parts[i].upper()

        elif part in ("-H", "--header"):
            i += 1
            header_line = parts[i]
            if ":" in header_line:
                k, v = header_line.split(":", 1)
                headers[k.strip()] = v.strip()

        elif part in ("--data", "--data-raw", "--data-binary", "-d", "--data-ascii"):
            i += 1
            body_raw = parts[i]
            if method == "GET":
                method = "POST"

        elif part.startswith("http://") or part.startswith("https://"):
            url = part

        i += 1

    if not url:
        raise ValueError("Could not find URL in curl command.")

    parsed_url = urlparse(url)

    base_endpoint = parsed_url.path or "/"
    query_params = dict(parse_qsl(parsed_url.query, keep_blank_values=True))

    endpoint = base_endpoint
    if parsed_url.query:
        endpoint += f"?{parsed_url.query}"

    content_type = headers.get("Content-Type") or headers.get("content-type") or ""
    body_raw = normalize_body_raw(body_raw)

    body_form: Dict[str, str] = {}
    if body_raw and "application/x-www-form-urlencoded" in content_type.lower():
        body_form = dict(parse_qsl(body_raw, keep_blank_values=True))

    return {
        "method": method,
        "host": parsed_url.netloc,
        "endpoint": endpoint,
        "base_endpoint": base_endpoint,
        "query_params": query_params,
        "use_tls": parsed_url.scheme == "https",
        "headers": headers,
        "content_type": content_type,
        "body_raw": body_raw,
        "body_form": body_form,
        "original_url": url,
    }


def detect_body_mode(content_type: str, body_raw: str | None, query_params: Dict[str, str]) -> str:
    if not body_raw and query_params:
        return "query"

    if not body_raw:
        return "none"

    content_type_lower = content_type.lower()

    if "multipart/form-data" in content_type_lower:
        return "multipart"

    if "application/x-www-form-urlencoded" in content_type_lower:
        return "form"

    if "application/json" in content_type_lower:
        return "json"

    try:
        json.loads(body_raw)
        return "json"
    except Exception:
        return "raw"


def get_boundary_from_content_type(content_type: str) -> str:
    match = re.search(r'boundary=([^;]+)', content_type, re.IGNORECASE)
    if not match:
        raise ValueError("multipart/form-data detected, but boundary was not found in Content-Type.")

    boundary = match.group(1).strip().strip('"')
    if boundary.startswith("--"):
        boundary = boundary[2:]

    return boundary


def parse_multipart_fields(body_raw: str, boundary: str) -> Dict[str, str]:
    if not body_raw:
        raise ValueError("Multipart body is empty.")

    normalized = body_raw.replace("\r\n", "\n").replace("\r", "\n")

    markers = [
        f"--{boundary}",
        boundary,
        f"--{boundary}--",
    ]

    chosen_marker = None
    for marker in markers:
        if marker in normalized:
            if marker == boundary:
                chosen_marker = boundary
            else:
                chosen_marker = f"--{boundary}"
            break

    if chosen_marker is None:
        first_line = normalized.split("\n", 1)[0].strip()
        if first_line.startswith("--"):
            chosen_marker = first_line
        else:
            raise ValueError("Could not find multipart boundary inside curl body.")

    parts = normalized.split(chosen_marker)
    fields: Dict[str, str] = {}

    for part in parts:
        part = part.strip()
        if not part or part == "--":
            continue

        if part.endswith("--"):
            part = part[:-2].strip()

        if "\n\n" not in part:
            continue

        header_block, value = part.split("\n\n", 1)
        value = value.rstrip("\n")

        name_match = re.search(r'name="([^"]+)"', header_block, re.IGNORECASE)
        if not name_match:
            continue

        field_name = name_match.group(1)
        fields[field_name] = value

    if not fields:
        raise ValueError("Could not parse multipart/form-data fields from curl body.")

    return fields


def encode_multipart_fields(fields: Dict[str, Any], boundary: str) -> str:
    if boundary.startswith("--"):
        boundary = boundary[2:]

    lines: list[str] = []

    for key, value in fields.items():
        lines.append(f"--{boundary}")
        lines.append(f'Content-Disposition: form-data; name="{key}"')
        lines.append("")
        lines.append("" if value is None else str(value))

    lines.append(f"--{boundary}--")
    lines.append("")
    return "\r\n".join(lines)


def get_nested_value(obj: Any, dotted_key: str) -> Any:
    current = obj
    for part in dotted_key.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            if idx >= len(current):
                return None
            current = current[idx]
        else:
            return None
    return current


def set_nested_value(obj: Any, dotted_key: str, value: Any) -> Any:
    parts = dotted_key.split(".")
    current = obj

    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            raise ValueError(f"Cannot set nested key '{dotted_key}' in current structure.")

    last = parts[-1]
    if isinstance(current, dict):
        current[last] = value
        return obj
    if isinstance(current, list) and last.isdigit():
        current[int(last)] = value
        return obj

    raise ValueError(f"Cannot set nested key '{dotted_key}' in current structure.")


def build_query_template(base_endpoint: str, query_params: Dict[str, str], prompt_param: str) -> tuple[Any, str, Dict[str, Any]]:
    if prompt_param not in query_params:
        raise ValueError(f"Prompt field '{prompt_param}' not found in query params.")

    updated = dict(query_params)
    existing = updated[prompt_param]
    updated[prompt_param] = "{PROMPT}"

    endpoint_template = base_endpoint
    if updated:
        endpoint_template += "?" + urlencode(updated)

    return None, str(existing), {"endpoint_template": endpoint_template}


def build_body_template(body_mode: str, body_raw: str | None, prompt_param: str) -> tuple[Any, str, Dict[str, Any]]:
    metadata: Dict[str, Any] = {}

    if body_mode == "json":
        try:
            safe_body_raw = sanitize_json_text(body_raw or "{}")
            parsed = json.loads(safe_body_raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse JSON body: {exc}. "
                "This usually means the curl body contains invalid JSON or was modified while normalizing."
            ) from exc

        existing = get_nested_value(parsed, prompt_param)
        if existing is None:
            raise ValueError(f"Prompt field '{prompt_param}' not found in JSON body.")
        updated = deepcopy(parsed)
        set_nested_value(updated, prompt_param, "{PROMPT}")
        return updated, str(existing), metadata

    if body_mode == "form":
        parsed = dict(parse_qsl(body_raw or "", keep_blank_values=True))
        if prompt_param not in parsed:
            raise ValueError(f"Prompt field '{prompt_param}' not found in form body.")
        existing = parsed[prompt_param]
        parsed[prompt_param] = "{PROMPT}"
        return parsed, str(existing), metadata

    if body_mode == "multipart":
        raise RuntimeError("Multipart must be handled separately.")

    if body_mode == "raw":
        if not body_raw:
            raise ValueError("Raw body is empty.")
        if "{PROMPT}" in body_raw:
            return body_raw, "{PROMPT}", metadata
        raise ValueError("Raw body is not JSON/form/multipart. Put {PROMPT} manually in curl body for raw mode.")

    return None, "", metadata


def build_multipart_template(
    body_raw: str,
    content_type: str,
    prompt_param: str,
) -> tuple[Dict[str, str], str, Dict[str, Any]]:
    boundary = get_boundary_from_content_type(content_type)
    fields = parse_multipart_fields(body_raw, boundary)

    if prompt_param not in fields:
        raise ValueError(f"Prompt field '{prompt_param}' not found in multipart form fields.")

    existing = fields[prompt_param]
    fields[prompt_param] = "{PROMPT}"

    return fields, str(existing), {"multipart_boundary": boundary}


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def seed_dataset_file(target_path: Path, base_path: Path) -> None:
    ensure_parent_dir(target_path)

    if target_path.exists():
        return

    if base_path.exists():
        target_path.write_text(base_path.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        target_path.write_text("", encoding="utf-8")


def ensure_default_datasets() -> None:
    seed_dataset_file(TARGET_RULE_DISCLOSURE_PATH, BASE_RULE_DISCLOSURE_PATH)
    seed_dataset_file(TARGET_PROMPT_INJECTION_PATH, BASE_PROMPT_INJECTION_PATH)


def build_dataset_entry(
    name: str,
    attack_type: str,
    path: Path,
    success_substrings: List[str],
) -> Dict[str, Any]:
    return {
        "name": name,
        "attack_type": attack_type,
        "path": str(path),
        "results_file": f"{name}.jsonl",
        "success_substring": success_substrings[0] if success_substrings else "",
        "success_substrings": success_substrings,
    }


def get_available_dataset_catalog(target_name: str) -> Dict[str, Dict[str, Any]]:
    target_rule_path = Path("datasets") / "targets" / target_name / f"{target_name}_rule_disclosure.txt"
    target_prompt_path = Path("datasets") / "targets" / target_name / f"{target_name}_prompt_injection.txt"

    return {
        "base_rule_disclosure": {
            "name": "base_rule_disclosure",
            "attack_type": "rule_disclosure",
            "path": BASE_RULE_DISCLOSURE_PATH,
        },
        "base_prompt_injection": {
            "name": "base_prompt_injection",
            "attack_type": "prompt_injection",
            "path": BASE_PROMPT_INJECTION_PATH,
        },
        f"{target_name}_rule_disclosure": {
            "name": f"{target_name}_rule_disclosure",
            "attack_type": "rule_disclosure",
            "path": target_rule_path,
        },
        f"{target_name}_prompt_injection": {
            "name": f"{target_name}_prompt_injection",
            "attack_type": "prompt_injection",
            "path": target_prompt_path,
        },
    }


def ask_dataset_mode() -> str:
    print("\nSelect dataset mode:")
    print("1. Base only")
    print("2. Target only")
    print("3. Base + Target")
    print("4. Custom selection")
    print("5. All")
    return ask_choice("Choose option", ["1", "2", "3", "4", "5"], "3")


def select_datasets(target_name: str, success_substrings: List[str]) -> List[Dict[str, Any]]:
    catalog = get_available_dataset_catalog(target_name)
    selected_keys: List[str] = []

    mode = ask_dataset_mode()

    target_rule_key = f"{target_name}_rule_disclosure"
    target_prompt_key = f"{target_name}_prompt_injection"

    if mode == "1":
        selected_keys = [
            "base_rule_disclosure",
            "base_prompt_injection",
        ]
    elif mode == "2":
        selected_keys = [
            target_rule_key,
            target_prompt_key,
        ]
    elif mode == "3":
        selected_keys = [
            "base_rule_disclosure",
            "base_prompt_injection",
            target_rule_key,
            target_prompt_key,
        ]
    elif mode == "4":
        print("")
        for key in [
            "base_rule_disclosure",
            "base_prompt_injection",
            target_rule_key,
            target_prompt_key,
        ]:
            item = catalog[key]
            include = ask_yes_no(f"Include {item['name']}? (y/n)", "n")
            if include:
                selected_keys.append(key)
    elif mode == "5":
        selected_keys = [
            "base_rule_disclosure",
            "base_prompt_injection",
            target_rule_key,
            target_prompt_key,
        ]

    if not selected_keys:
        print("[!] No dataset selected. Falling back to target rule disclosure only.")
        selected_keys = [target_rule_key]

    seen = set()
    datasets: List[Dict[str, Any]] = []

    for key in selected_keys:
        if key in seen:
            continue
        seen.add(key)

        item = catalog[key]
        datasets.append(
            build_dataset_entry(
                name=item["name"],
                attack_type=item["attack_type"],
                path=item["path"],
                success_substrings=success_substrings,
            )
        )

    return datasets


def build_config_interactive(parsed: Dict[str, Any]) -> Dict[str, Any]:
    print("\n[+] Parsed curl successfully")
    print(f"    Method   : {parsed['method']}")
    print(f"    Host     : {parsed['host']}")
    print(f"    Endpoint : {parsed['endpoint']}")
    print(f"    TLS      : {parsed['use_tls']}")
    print(f"    Headers  : {list(parsed['headers'].keys())}")

    default_target_name = "app"
    target_name = ask("Target name", default_target_name).strip() or default_target_name

    keep_noisy = ask_yes_no("Keep noisy browser headers? (y/n)", "n")
    headers = parsed["headers"] if keep_noisy else clean_headers(parsed["headers"])

    if not headers:
        headers = {"Content-Type": "application/json"}

    content_type = headers.get("Content-Type") or headers.get("content-type") or parsed.get("content_type", "")
    body_mode = detect_body_mode(content_type, parsed.get("body_raw"), parsed.get("query_params", {}))

    print(f"    Body mode: {body_mode}")

    extra: Dict[str, Any] = {}

    if body_mode == "query":
        query_items = list(parsed.get("query_params", {}).items())
        if not query_items:
            raise ValueError("GET query mode detected, but no query parameters were found.")

        prompt_param = choose_from_list("\n[+] Detected URL query parameters:", query_items)
        body_template, original_prompt_value, extra = build_query_template(
            parsed["base_endpoint"],
            parsed["query_params"],
            prompt_param,
        )

    elif body_mode == "form":
        form_items = list(parsed.get("body_form", {}).items())
        if not form_items:
            raise ValueError("Form body mode detected, but no form parameters were found.")

        prompt_param = choose_from_list("\n[+] Detected form body parameters:", form_items)
        body_template, original_prompt_value, extra = build_body_template(
            body_mode=body_mode,
            body_raw=parsed.get("body_raw"),
            prompt_param=prompt_param,
        )

    else:
        prompt_param = ask("Request field to inject prompt into", "prompt")

        if body_mode == "multipart":
            body_template, original_prompt_value, extra = build_multipart_template(
                body_raw=parsed["body_raw"],
                content_type=content_type,
                prompt_param=prompt_param,
            )
        else:
            body_template, original_prompt_value, extra = build_body_template(
                body_mode=body_mode,
                body_raw=parsed.get("body_raw"),
                prompt_param=prompt_param,
            )

    print(f"[+] Found current prompt example value: {original_prompt_value!r}")

    response_field = ask("Response field to capture", "llm_output")
    success_raw = ask("Success substrings for scorer (comma separated)", "password,secret,flag,token,key")
    timeout = ask("Timeout in seconds", "30")

    success_substrings = [part.strip() for part in success_raw.split(",") if part.strip()]
    datasets = select_datasets(target_name=target_name, success_substrings=success_substrings)

    config: Dict[str, Any] = {
        "name": target_name,
        "use_tls": parsed["use_tls"],
        "host": parsed["host"],
        "method": parsed["method"],
        "endpoint": extra.get("endpoint_template", parsed["endpoint"]),
        "headers": headers,
        "body_mode": body_mode,
        "body_template": body_template,
        "prompt_param": prompt_param,
        "prompt_placeholder": "{PROMPT}",
        "response_field": response_field,
        "success_substring": success_substrings[0] if success_substrings else "",
        "success_substrings": success_substrings,
        "timeout": int(timeout),
        "datasets": datasets,
    }

    config.update(extra)
    return config


def replace_prompt_in_template(template: Any, prompt: str) -> Any:
    if isinstance(template, dict):
        return {k: replace_prompt_in_template(v, prompt) for k, v in template.items()}
    if isinstance(template, list):
        return [replace_prompt_in_template(v, prompt) for v in template]
    if isinstance(template, str) and template == "{PROMPT}":
        return prompt
    return template


def render_request_parts(config: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    body_mode = config.get("body_mode", "json")
    headers = dict(config.get("headers", {}))
    template = config.get("body_template")
    endpoint = config.get("endpoint", "/")

    if body_mode == "query":
        return {
            "endpoint": endpoint.replace("{PROMPT}", prompt),
            "body_mode": "query",
            "headers": headers,
            "payload": None,
        }

    if body_mode == "json":
        return {
            "endpoint": endpoint,
            "body_mode": "json",
            "headers": headers,
            "payload": replace_prompt_in_template(template, prompt),
        }

    if body_mode == "form":
        payload = replace_prompt_in_template(template, prompt)
        return {
            "endpoint": endpoint,
            "body_mode": "form",
            "headers": headers,
            "payload": payload,
        }

    if body_mode == "multipart":
        boundary = config["multipart_boundary"]
        payload_fields = replace_prompt_in_template(template, prompt)
        raw_body = encode_multipart_fields(payload_fields, boundary)

        lower_map = {k.lower(): k for k in headers}
        ct_key = lower_map.get("content-type", "Content-Type")
        headers[ct_key] = f"multipart/form-data; boundary={boundary}"

        return {
            "endpoint": endpoint,
            "body_mode": "multipart",
            "headers": headers,
            "payload": raw_body,
        }

    if body_mode == "raw":
        payload = replace_prompt_in_template(template, prompt)
        return {
            "endpoint": endpoint,
            "body_mode": "raw",
            "headers": headers,
            "payload": payload,
        }

    return {
        "endpoint": endpoint,
        "body_mode": "none",
        "headers": headers,
        "payload": None,
    }


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(config: Dict[str, Any], output_path: Path | None = None) -> Path:
    if output_path is None:
        config_name = f"{config['name']}.config.json"
        output_path = Path("configs") / config_name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def ensure_target_dataset_files(target_name: str) -> None:
    target_dir = Path("datasets") / "targets" / target_name
    target_rule = target_dir / f"{target_name}_rule_disclosure.txt"
    target_prompt = target_dir / f"{target_name}_prompt_injection.txt"

    seed_dataset_file(target_rule, BASE_RULE_DISCLOSURE_PATH)
    seed_dataset_file(target_prompt, BASE_PROMPT_INJECTION_PATH)


def main() -> None:
    curl_text = prompt_multiline_input("[+] Paste curl command")
    parsed = parse_curl(curl_text)
    ensure_default_datasets()

    config = build_config_interactive(parsed)
    ensure_target_dataset_files(config["name"])

    output_path = save_config(config)

    print("\n[+] Config written successfully")
    print(f"    {output_path.resolve()}")

    print("\n[+] Dataset entries selected:")
    for ds in config.get("datasets", []):
        print(f"    - {ds['name']}: {ds['path']}")

    print("\n[+] Generated config preview:")
    print(json.dumps(config, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()