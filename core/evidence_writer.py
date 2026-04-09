from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from models.attack_state import AttackState


def write_case_json(output_dir: str | Path, state: AttackState) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    case_file = output_path / f"{state.case_id}.json"
    case_file.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return case_file


def build_run_summary(states: List[AttackState]) -> Dict[str, Any]:
    total = len(states)
    by_verdict = {
        "success": 0,
        "suspicious": 0,
        "failed": 0,
    }

    keyword_counts: Dict[str, int] = {}

    for state in states:
        verdict = state.final_verdict or "failed"
        by_verdict[verdict] = by_verdict.get(verdict, 0) + 1

        for turn in state.turns:
            matches = turn.evaluation.get("indicator_matches", [])
            for match in matches:
                keyword_counts[match] = keyword_counts.get(match, 0) + 1

    return {
        "total_cases": total,
        "verdicts": by_verdict,
        "keyword_counts": dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)),
        "cases": [
            {
                "case_id": s.case_id,
                "category": s.category,
                "goal": s.goal,
                "base_prompt": s.base_prompt,
                "final_verdict": s.final_verdict,
                "stop_reason": s.stop_reason,
                "turn_count": s.turn_count(),
            }
            for s in states
        ],
    }


def write_run_summary(output_dir: str | Path, summary: Dict[str, Any]) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    summary_file = output_path / "run_summary.json"
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary_file