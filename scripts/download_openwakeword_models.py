#!/usr/bin/env python3
from __future__ import annotations

import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

try:
    from urllib3.exceptions import NotOpenSSLWarning

    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

from openwakeword.utils import download_models


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    target_dir = root / "models" / "openwakeword"
    target_dir.mkdir(parents=True, exist_ok=True)
    download_models(["hey_jarvis_v0.1"], target_directory=str(target_dir))
    print("openWakeWord hey_jarvis model is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
