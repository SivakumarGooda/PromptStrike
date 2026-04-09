from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from queue import Empty, Queue


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
        elapsed = max(time.time() - self.started_at, 0.001)
        return self.total_requests / elapsed


class RunController:
    def __init__(self) -> None:
        self._queue: Queue[str] = Queue()
        self._paused = False
        self._stop_requested = False
        self._listener_started = False
        self._lock = threading.Lock()

    def start_listener(self) -> None:
        if self._listener_started:
            return

        self._listener_started = True
        thread = threading.Thread(target=self._input_loop, daemon=True)
        thread.start()

    def _input_loop(self) -> None:
        while True:
            try:
                raw = input().strip().lower()
            except EOFError:
                break
            except Exception:
                continue

            if raw:
                self._queue.put(raw)

    def poll_commands(self) -> None:
        while True:
            try:
                cmd = self._queue.get_nowait()
            except Empty:
                break

            if cmd == "p":
                with self._lock:
                    self._paused = True
                print("\n[!] Pause requested. Tool will pause at the next safe point.\n")

            elif cmd == "r":
                with self._lock:
                    self._paused = False
                print("\n[+] Resume requested.\n")

            elif cmd == "q":
                with self._lock:
                    self._stop_requested = True
                print("\n[!] Stop requested. Tool will stop cleanly after the current case.\n")

    def wait_if_paused(self) -> None:
        printed = False

        while True:
            self.poll_commands()

            with self._lock:
                if not self._paused:
                    if printed:
                        print("[+] Resumed\n")
                    return

            if not printed:
                print("\n[!] Paused. Type 'r' and press Enter to resume.\n")
                printed = True

            time.sleep(1.5)

    def stop_requested(self) -> bool:
        self.poll_commands()
        with self._lock:
            return self._stop_requested