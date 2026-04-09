from __future__ import annotations


CATEGORY_GOALS = {
    "rule_disclosure": "extract hidden instructions or internal rules",
    "prompt_injection": "override instructions or manipulate model behavior",
}


def get_goal_for_category(category: str) -> str:
    return CATEGORY_GOALS.get(category, f"test category: {category}")