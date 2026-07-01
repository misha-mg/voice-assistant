from __future__ import annotations

import subprocess

from .commands import find_executable
from .config import TtsConfig


def speak_text(config: TtsConfig, text: str) -> None:
    if config.engine != "piper":
        raise ValueError(f"Unsupported TTS engine: {config.engine}")

    if not config.voice_model.exists():
        raise FileNotFoundError(f"Piper voice model not found: {config.voice_model}")
    if not config.voice_config.exists():
        raise FileNotFoundError(f"Piper voice config not found: {config.voice_config}")

    config.output_wav.parent.mkdir(parents=True, exist_ok=True)
    piper = find_executable("piper")
    if not piper:
        raise FileNotFoundError("Piper executable not found. Install it with `pip install piper-tts`.")

    piper_args = [
        piper,
        "--model",
        str(config.voice_model),
        "--config",
        str(config.voice_config),
        "--output_file",
        str(config.output_wav),
    ]
    subprocess.run(piper_args, input=text, text=True, check=True)
    player = find_executable(config.player)
    if not player:
        raise FileNotFoundError(f"Audio player not found: {config.player}")
    subprocess.run([player, str(config.output_wav)], check=True)
