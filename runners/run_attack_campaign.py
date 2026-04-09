from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.attack_loop import run_attack_case
from core.config_adapter import adapt_config_to_sender
from core.dataset_loader import load_attack_payloads
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


def print_live_stats(stats: RunStats, category: str, case_index: int, total_cases: int) -> None:
    print("\n" + "=" * 72)
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


def run_campaign(
    config_path: str | Path,
    datasets_root: str | Path,
    target_name: str,
    category: str,
    output_root: str | Path,
    max_turns: int = 5,
    max_total_requests: int = 100,
) -> None:
    raw_config = load_target_config(config_path)
    sender_config = adapt_config_to_sender(raw_config)
    sender = TargetSender(sender_config)

    payloads = load_attack_payloads(
        datasets_root=datasets_root,
        target_name=target_name,
        category=category,
    )

    if not payloads:
        print(f"[-] No payloads found for category: {category}")
        return

    goal = get_goal_for_category(category)

    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    jsonl_file = output_root / f"{category}.jsonl"
    html_file = output_root / f"{category}.html"

    if jsonl_file.exists():
        jsonl_file.unlink()

    stats = RunStats(total_cases=len(payloads))
    controller = RunController()
    controller.start_listener()

    print(f"[+] Starting campaign: {category}")
    print(f"[+] Payload count     : {len(payloads)}")
    print(f"[+] Max total requests: {max_total_requests}")
    print("[+] Runtime controls  : p=pause, r=resume, q=stop after current case")
    print("")

    for idx, payload in enumerate(payloads, start=1):
        controller.poll_commands()
        controller.wait_if_paused()

        if controller.stop_requested():
            print("[!] Stop requested. Ending campaign cleanly.")
            break

        if stats.total_requests >= max_total_requests:
            print("[!] Max total request limit reached. Ending campaign.")
            break

        print_live_stats(stats, category, idx - 1, len(payloads))
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

        if state.latest_turn() and state.latest_turn().error:
            stats.error_count += 1

        stats.completed_cases += 1

        append_case_jsonl(jsonl_file, state.to_dict())

        generate_html_report_from_jsonl(
            jsonl_path=jsonl_file,
            html_path=html_file,
            title=f"{category.replace('_', ' ').title()} Report",
        )

        print(f"[+] Updated report: {html_file}")

        if stats.total_requests >= max_total_requests:
            print("[!] Max total request limit reached. Ending campaign.")
            break

    print_live_stats(stats, category, stats.completed_cases, len(payloads))
    print(f"[+] Campaign finished: {category}")
    print(f"[+] JSONL report: {jsonl_file}")
    print(f"[+] HTML report : {html_file}")