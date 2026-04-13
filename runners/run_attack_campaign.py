from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.attack_loop import run_attack_case
from core.config_adapter import adapt_config_to_sender
from core.goals import get_goal_for_category
from core.html_report import generate_html_report_from_jsonl
from core.run_control import RunController, RunStats
from core.sender import TargetSender


def load_target_config(config_path: str | Path) -> Dict[str, Any]:
    path = Path(config_path)
    return json.loads(path.read_text(encoding="utf-8"))


def render_progress_bar(current: int, total: int, width: int = 32) -> str:
    if total <= 0:
        total = 1
    ratio = min(max(current / total, 0.0), 1.0)
    filled = int(width * ratio)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {current}/{total}"


def print_live_stats(
    stats: RunStats,
    category: str,
    case_index: int,
    total_cases: int,
    dataset_name: str | None = None,
) -> None:
    print("\n" + "=" * 72)
    if dataset_name:
        print(f"[+] Dataset       : {dataset_name}")
    print(f"[+] Category      : {category}")
    print(f"[+] Progress      : {render_progress_bar(case_index, total_cases)}")
    print(f"[+] Cases done    : {stats.completed_cases}/{stats.total_cases}")
    print(f"[+] Requests sent : {stats.total_requests}")
    print(f"[+] Req/sec       : {stats.requests_per_second():.2f}")
    print(
        f"[+] Verdicts      : success={stats.success_count} | "
        f"suspicious={stats.suspicious_count} | failed={stats.failed_count} | errors={stats.error_count}"
    )
    print("=" * 72 + "\n")


def append_case_jsonl(jsonl_path: Path, case_data: Dict[str, Any]) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(case_data, ensure_ascii=False) + "\n")


def load_payloads_from_file(dataset_path: str | Path) -> List[str]:
    path = Path(dataset_path)
    if not path.exists():
        print(f"[-] Dataset file not found: {path}")
        return []

    payloads: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        payloads.append(line)

    return payloads


def normalize_dataset_entry(ds: Dict[str, Any]) -> Dict[str, Any]:
    name = ds.get("name", "unnamed_dataset")
    path = ds.get("path")
    attack_type = ds.get("attack_type")

    if not attack_type:
        joined = f"{name} {path}".lower()
        if "prompt_injection" in joined:
            attack_type = "prompt_injection"
        elif "rule_disclosure" in joined:
            attack_type = "rule_disclosure"
        else:
            attack_type = "generic"

    results_file = ds.get("results_file", f"{name}.jsonl")
    success_substring = ds.get("success_substring", "")
    success_substrings = ds.get("success_substrings")

    if success_substrings is None:
        success_substrings = [success_substring] if success_substring else []

    return {
        "name": name,
        "path": path,
        "attack_type": attack_type,
        "results_file": results_file,
        "success_substring": success_substring,
        "success_substrings": success_substrings,
    }


def run_single_dataset(
    sender: TargetSender,
    dataset_cfg: Dict[str, Any],
    output_root: str | Path,
    controller: RunController,
    max_turns: int = 5,
    max_total_requests: int = 100,
) -> None:
    dataset_cfg = normalize_dataset_entry(dataset_cfg)

    dataset_name = dataset_cfg["name"]
    dataset_path = dataset_cfg["path"]
    category = dataset_cfg["attack_type"]

    if not dataset_path:
        print(f"[-] Skipping dataset '{dataset_name}': missing path")
        return

    payloads = load_payloads_from_file(dataset_path)

    if not payloads:
        print(f"[-] No payloads found for dataset: {dataset_name}")
        return

    goal = get_goal_for_category(category)

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    jsonl_file = output_root / dataset_cfg["results_file"]
    html_file = output_root / f"{Path(dataset_cfg['results_file']).stem}.html"

    if jsonl_file.exists():
        jsonl_file.unlink()

    stats = RunStats(total_cases=len(payloads))

    print(f"[+] Starting dataset    : {dataset_name}")
    print(f"[+] Attack type         : {category}")
    print(f"[+] Dataset path        : {dataset_path}")
    print(f"[+] Payload count       : {len(payloads)}")
    print(f"[+] Max total requests  : {max_total_requests}")
    print("[+] Runtime controls    : p=pause, r=resume, q=stop after current case")
    print("")

    for idx, payload in enumerate(payloads, start=1):
        controller.poll_commands()
        controller.wait_if_paused()

        if controller.stop_requested():
            print("[!] Stop requested. Ending dataset cleanly.")
            break

        if stats.total_requests >= max_total_requests:
            print("[!] Max total request limit reached for this dataset. Ending dataset.")
            break

        print_live_stats(
            stats=stats,
            category=category,
            case_index=idx - 1,
            total_cases=len(payloads),
            dataset_name=dataset_name,
        )
        print(f"[+] Running case {idx}/{len(payloads)}")
        print(f"[+] Base payload: {payload[:180]}")

        state = run_attack_case(
            case_id=f"{category[:2]}-{idx:03d}",
            category=category,
            goal=goal,
            base_prompt=payload,
            send_prompt=sender.send_prompt,
            max_turns=max_turns,
            controller=controller,
            stats=stats,
        )

        state_dict = state.to_dict()
        state_dict["dataset_name"] = dataset_name
        state_dict["dataset_path"] = dataset_path
        state_dict["attack_type"] = category
        state_dict["success_substrings"] = dataset_cfg["success_substrings"]

        if state.latest_turn() and state.latest_turn().error:
            stats.error_count += 1

        stats.completed_cases += 1

        append_case_jsonl(jsonl_file, state_dict)

        generate_html_report_from_jsonl(
            jsonl_path=jsonl_file,
            html_path=html_file,
            title=f"{dataset_name.replace('_', ' ').title()} Report",
        )

        print(f"[+] Updated report: {html_file}")

        if stats.total_requests >= max_total_requests:
            print("[!] Max total request limit reached for this dataset. Ending dataset.")
            break

    print_live_stats(
        stats=stats,
        category=category,
        case_index=stats.completed_cases,
        total_cases=len(payloads),
        dataset_name=dataset_name,
    )
    print(f"[+] Dataset finished: {dataset_name}")
    print(f"[+] JSONL report    : {jsonl_file}")
    print(f"[+] HTML report     : {html_file}")
    print("")


def run_campaign(
    config_path: str | Path,
    output_root: str | Path,
    max_turns: int = 5,
    max_total_requests: int = 100,
) -> None:
    raw_config = load_target_config(config_path)
    sender_config = adapt_config_to_sender(raw_config)
    sender = TargetSender(sender_config)

    datasets = raw_config.get("datasets", [])

    # Backward compatibility with old single-dataset config
    if not datasets and raw_config.get("dataset_path"):
        legacy_name = raw_config.get("name", "target")
        legacy_dataset_path = raw_config["dataset_path"]

        if "prompt_injection" in str(legacy_dataset_path).lower():
            legacy_attack_type = "prompt_injection"
        elif "rule_disclosure" in str(legacy_dataset_path).lower():
            legacy_attack_type = "rule_disclosure"
        else:
            legacy_attack_type = "generic"

        datasets = [
            {
                "name": f"{legacy_name}_{legacy_attack_type}",
                "path": legacy_dataset_path,
                "attack_type": legacy_attack_type,
                "results_file": raw_config.get("results_file", f"{legacy_attack_type}.jsonl"),
                "success_substring": raw_config.get("success_substring", ""),
                "success_substrings": raw_config.get("success_substrings", []),
            }
        ]

    if not datasets:
        print("[-] No datasets found in config.")
        return

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"[+] Loaded config     : {config_path}")
    print(f"[+] Total datasets    : {len(datasets)}")
    print(f"[+] Output root       : {output_root}")
    print("")

    # One controller for the full campaign.
    controller = RunController()
    controller.start_listener()

    for ds in datasets:
        if controller.stop_requested():
            print("[!] Stop requested. Ending campaign before next dataset.")
            break

        run_single_dataset(
            sender=sender,
            dataset_cfg=ds,
            output_root=output_root,
            controller=controller,
            max_turns=max_turns,
            max_total_requests=max_total_requests,
        )

    print("[+] All selected datasets finished.")