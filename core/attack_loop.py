from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from core.evaluator import evaluate_response
from core.mutator import mutate_prompt
from core.observer import observe_response
from core.run_control import RunController, RunStats
from core.strategy import choose_next_strategy
from models.attack_state import AttackState


SendPromptFn = Callable[[str], Dict[str, Any]]
ProgressFn = Callable[[str], None]


def run_attack_case(
    case_id: str,
    category: str,
    goal: str,
    base_prompt: str,
    send_prompt: SendPromptFn,
    max_turns: int = 5,
    controller: Optional[RunController] = None,
    stats: Optional[RunStats] = None,
    progress_callback: Optional[ProgressFn] = None,
) -> AttackState:
    state = AttackState(
        case_id=case_id,
        category=category,
        goal=goal,
        base_prompt=base_prompt,
        current_prompt=base_prompt,
        max_turns=max_turns,
    )

    def emit(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    emit(f"    [*] Starting case: {case_id}")
    emit(f"    [*] Base prompt  : {base_prompt[:200]}")

    while not state.is_finished():
        if controller:
            controller.poll_commands()
            controller.wait_if_paused()

        strategy = choose_next_strategy(state)
        if strategy is None:
            state.stop_reason = "no_more_strategies"
            emit("    [-] No more strategies left to try")
            break

        latest = state.latest_turn()
        last_response_text = latest.response_text if latest else ""

        current_prompt = mutate_prompt(
            base_prompt=state.base_prompt,
            strategy=strategy,
            last_response_text=last_response_text,
        )
        state.current_prompt = current_prompt

        emit(f"      -> Turn     : {state.turn_count() + 1}/{state.max_turns}")
        emit(f"      -> Strategy : {strategy}")
        emit(f"      -> Prompt   : {current_prompt[:300]}")

        result = send_prompt(current_prompt)

        if stats:
            stats.total_requests += 1

        status_code = int(result.get("status_code", 0))
        response_text = str(result.get("response_text", "") or "")

        observation = observe_response(
            response_text=response_text,
            status_code=status_code,
        )

        evaluation = evaluate_response(
            response_text=response_text,
            observation=observation,
        )

        state.add_turn(
            strategy=strategy,
            prompt=current_prompt,
            response_text=response_text,
            response_status=status_code,
            observation=observation,
            evaluation=evaluation,
            request_data=result.get("request", {}),
            response_data={
                "raw_response_text": result.get("raw_response_text", ""),
                "response_json": result.get("response_json"),
                "response_headers": result.get("response_headers", {}),
            },
            latency_ms=int(result.get("latency_ms", 0) or 0),
            error=result.get("error"),
        )

        emit(f"      -> HTTP       : {status_code}")
        emit(f"      -> Observation: {observation.get('label')}")
        emit(f"      -> Eval       : {evaluation.get('verdict')} (score={evaluation.get('score')})")
        emit(f"      -> Latency    : {result.get('latency_ms', 0)} ms")

        if result.get("error"):
            emit(f"      -> Error      : {result.get('error')}")

        verdict = evaluation.get("verdict", "failed")

        if verdict == "success":
            state.final_verdict = "success"
            state.stop_reason = "evaluation_success"
            emit("    [+] Case marked as SUCCESS")
            break

        if verdict == "suspicious" and state.turn_count() >= 2:
            state.final_verdict = "suspicious"
            state.stop_reason = "suspicious_enough_to_review"
            emit("    [!] Case marked as SUSPICIOUS for review")
            break

    if state.final_verdict is None:
        latest = state.latest_turn()
        if latest:
            state.final_verdict = latest.evaluation.get("verdict", "failed")
        else:
            state.final_verdict = "failed"

    if stats:
        if state.final_verdict == "success":
            stats.success_count += 1
        elif state.final_verdict == "suspicious":
            stats.suspicious_count += 1
        else:
            stats.failed_count += 1

    emit(f"    [*] Final verdict: {state.final_verdict}")
    emit(f"    [*] Stop reason  : {state.stop_reason}")
    emit(f"    [*] Total turns  : {state.turn_count()}")

    return state