#!/usr/bin/env python3
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path


VOICE_BASE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    "en/en_US/lessac/medium"
)
FILES = [
    "en_US-lessac-medium.onnx",
    "en_US-lessac-medium.onnx.json",
]


def download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        print(f"Already exists: {target}")
        return

    print(f"Downloading {url}")
    with urllib.request.urlopen(url) as response:
        target.write_bytes(response.read())
    print(f"Saved: {target}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    target_dir = root / "models" / "piper"

    for filename in FILES:
        download(f"{VOICE_BASE_URL}/{filename}", target_dir / filename)

    print("Piper English voice is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
