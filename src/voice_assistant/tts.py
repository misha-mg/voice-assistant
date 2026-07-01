from __future__ import annotations

import subprocess

from .config import TtsConfig


def speak_text(config: TtsConfig, text: str) -> None:
    if config.engine != "piper":
        raise ValueError(f"Unsupported TTS engine: {config.engine}")

    if not config.voice_model.exists():
        raise FileNotFoundError(f"Piper voice model not found: {config.voice_model}")
    if not config.voice_config.exists():
        raise FileNotFoundError(f"Piper voice config not found: {config.voice_config}")

    config.output_wav.parent.mkdir(parents=True, exist_ok=True)
    piper_args = [
        "piper",
        "--model",
        str(config.voice_model),
        "--config",
        str(config.voice_config),
        "--output_file",
        str(config.output_wav),
    ]
    subprocess.run(piper_args, input=text, text=True, check=True)
    subprocess.run([config.player, str(config.output_wav)], check=True)
