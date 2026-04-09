from __future__ import annotations

from typing import List, Optional

from models.attack_state import AttackState


DEFAULT_STRATEGY_ORDER = [
    "direct",
    "roleplay",
    "indirect",
    "debug",
    "summarize_rules",
    "developer_mode",
    "quoted_extraction",
    "continuation",
    "safe_audit",
    "translate_style",
]


OBSERVATION_STRATEGIES = {
    "empty": [
        "debug",
        "direct",
        "roleplay",
    ],
    "server_error": [
        "direct",
        "indirect",
    ],
    "client_error": [
        "direct",
        "indirect",
    ],
    "refusal": [
        "roleplay",
        "indirect",
        "debug",
        "developer_mode",
        "summarize_rules",
        "quoted_extraction",
        "continuation",
        "safe_audit",
        "translate_style",
    ],
    "possible_disclosure": [
        "quoted_extraction",
        "continuation",
        "summarize_rules",
        "safe_audit",
    ],
    "success": [],
    "unknown": [
        "indirect",
        "roleplay",
        "debug",
        "summarize_rules",
        "developer_mode",
        "safe_audit",
        "continuation",
    ],
}


def _first_unused(candidates: List[str], used: List[str]) -> Optional[str]:
    for item in candidates:
        if item not in used:
            return item
    return None


def choose_next_strategy(state: AttackState) -> Optional[str]:
    """
    Pick the next strategy based on the latest observation and what has already been used.

    Returns None if there is nothing meaningful left to try.
    """
    latest = state.latest_turn()

    if latest is None:
        return "direct"

    label = latest.observation.get("label", "unknown")
    used = state.used_strategies

    if label == "success":
        return None

    preferred = OBSERVATION_STRATEGIES.get(label, DEFAULT_STRATEGY_ORDER)
    next_strategy = _first_unused(preferred, used)

    if next_strategy:
        return next_strategy

    fallback = _first_unused(DEFAULT_STRATEGY_ORDER, used)
    if fallback:
        return fallback

    return None