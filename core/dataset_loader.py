from __future__ import annotations

from pathlib import Path
from typing import List


def _read_dataset_file(path: Path) -> List[str]:
    if not path.exists():
        return []

    items: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        items.append(line)
    return items


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []

    for item in items:
        key = item.strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)

    return result


def load_attack_payloads(
    datasets_root: str | Path,
    target_name: str,
    category: str,
) -> List[str]:
    """
    Example:
      target_name = "app.config"
      category = "prompt_injection"

    Loads:
      datasets/base/base_prompt_injection.txt
      datasets/targets/app.config/app.config_prompt_injection.txt
    """
    root = Path(datasets_root)

    base_file = root / "base" / f"base_{category}.txt"
    target_file = root / "targets" / target_name / f"{target_name}_{category}.txt"

    base_payloads = _read_dataset_file(base_file)
    target_payloads = _read_dataset_file(target_file)

    return _dedupe_keep_order(base_payloads + target_payloads)