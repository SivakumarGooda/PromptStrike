from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AttackTurn:
    turn_index: int
    strategy: str
    prompt: str
    response_text: str
    response_status: int
    observation: Dict[str, Any]
    evaluation: Dict[str, Any]
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0
    error: Optional[str] = None


@dataclass
class AttackState:
    case_id: str
    category: str
    goal: str
    base_prompt: str
    current_prompt: str
    max_turns: int = 5

    turns: List[AttackTurn] = field(default_factory=list)
    used_strategies: List[str] = field(default_factory=list)
    final_verdict: Optional[str] = None
    stop_reason: Optional[str] = None

    def add_turn(
        self,
        strategy: str,
        prompt: str,
        response_text: str,
        response_status: int,
        observation: Dict[str, Any],
        evaluation: Dict[str, Any],
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        latency_ms: int = 0,
        error: Optional[str] = None,
    ) -> None:
        turn = AttackTurn(
            turn_index=len(self.turns) + 1,
            strategy=strategy,
            prompt=prompt,
            response_text=response_text,
            response_status=response_status,
            observation=observation,
            evaluation=evaluation,
            request_data=request_data or {},
            response_data=response_data or {},
            latency_ms=latency_ms,
            error=error,
        )
        self.turns.append(turn)

        if strategy not in self.used_strategies:
            self.used_strategies.append(strategy)

    def turn_count(self) -> int:
        return len(self.turns)

    def is_finished(self) -> bool:
        if self.final_verdict is not None:
            return True
        if self.turn_count() >= self.max_turns:
            self.stop_reason = "max_turns_reached"
            return True
        return False

    def latest_turn(self) -> Optional[AttackTurn]:
        if not self.turns:
            return None
        return self.turns[-1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "goal": self.goal,
            "base_prompt": self.base_prompt,
            "current_prompt": self.current_prompt,
            "max_turns": self.max_turns,
            "used_strategies": self.used_strategies,
            "final_verdict": self.final_verdict,
            "stop_reason": self.stop_reason,
            "turns": [
                {
                    "turn_index": t.turn_index,
                    "strategy": t.strategy,
                    "prompt": t.prompt,
                    "response_text": t.response_text,
                    "response_status": t.response_status,
                    "observation": t.observation,
                    "evaluation": t.evaluation,
                    "request_data": t.request_data,
                    "response_data": t.response_data,
                    "latency_ms": t.latency_ms,
                    "error": t.error,
                }
                for t in self.turns
            ],
        }