from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class RunStats:
    total_cases: int = 0
    completed_cases: int = 0
    total_requests: int = 0
    success_count: int = 0
    suspicious_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    started_at: float = field(default_factory=time.time)

    def requests_per_second(self) -> float:
        elapsed = max(time.time() - self.started_at, 1e-6)
        return self.total_requests / elapsed


class RunController:
    """
    Runtime controls:
      p + Enter -> pause
      r + Enter -> resume
      q + Enter -> stop after current case

    Important:
    - Start only ONE listener for the whole campaign.
    - Reusing the same controller across datasets avoids stdin conflicts.
    """

    def __init__(self) -> None:
        self._paused = False
        self._stop_requested = False
        self._listener_started = False
        self._lock = threading.Lock()

    def start_listener(self) -> None:
        if self._listener_started:
            return

        self._listener_started = True
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def _listen_loop(self) -> None:
        while True:
            try:
                cmd = input().strip().lower()
            except EOFError:
                break
            except KeyboardInterrupt:
                with self._lock:
                    self._stop_requested = True
                print("\n[!] Keyboard interrupt received. Will stop after current case.")
                break

            if not cmd:
                continue

            if cmd == "p":
                with self._lock:
                    self._paused = True
                print("[!] Paused")

            elif cmd == "r":
                with self._lock:
                    self._paused = False
                print("[+] Resumed")

            elif cmd == "q":
                with self._lock:
                    self._stop_requested = True
                print("[!] Stop requested. Will stop after current case.")

    def poll_commands(self) -> None:
        # Kept for compatibility with existing runner logic.
        return

    def wait_if_paused(self) -> None:
        while True:
            with self._lock:
                paused = self._paused
                stop = self._stop_requested

            if stop or not paused:
                return

            time.sleep(0.1)

    def stop_requested(self) -> bool:
        with self._lock:
            return self._stop_requested

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused