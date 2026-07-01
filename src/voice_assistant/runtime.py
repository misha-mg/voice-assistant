from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


VALID_STATES = {
    "idle",
    "listening",
    "recording",
    "transcribing",
    "thinking",
    "speaking",
    "error",
}


def show_state(state: str, detail: str = "") -> None:
    if state not in VALID_STATES:
        raise ValueError(f"Unknown runtime state: {state}")
    suffix = f" {detail}" if detail else ""
    print(f"[{state}]{suffix}", flush=True)


@contextmanager
def runtime_state(state: str, detail: str = "") -> Iterator[None]:
    show_state(state, detail)
    yield
