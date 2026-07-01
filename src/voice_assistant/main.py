from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .config import AppConfig


def default_config_path() -> Path:
    return Path.cwd() / "config.toml"


def load_app_config(path: Optional[str]) -> "AppConfig":
    from .config import load_config

    return load_config(Path(path).expanduser() if path else default_config_path())


def trim_for_speech(text: str, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def command_check(config: "AppConfig") -> int:
    checks = [
        ("codex", shutil.which("codex")),
        ("piper", shutil.which("piper")),
        (config.tts.player, shutil.which(config.tts.player)),
    ]

    ok = True
    for name, path in checks:
        if path:
            print(f"OK: {name} -> {path}")
        else:
            ok = False
            print(f"Missing: {name}")

    for label, path in [
        ("Piper voice model", config.tts.voice_model),
        ("Piper voice config", config.tts.voice_config),
        ("Codex project dir", config.codex.project_dir),
    ]:
        if path.exists():
            print(f"OK: {label} -> {path}")
        else:
            ok = False
            print(f"Missing: {label} -> {path}")

    return 0 if ok else 1


def command_record(config: "AppConfig") -> int:
    from .audio import record_until_enter

    audio_path = config.root_dir / "logs" / "last-input.wav"
    record_until_enter(config.audio, audio_path)
    return 0


def command_speak(config: "AppConfig", text: str) -> int:
    from .tts import speak_text

    speak_text(config.tts, text)
    return 0


def command_ask(config: "AppConfig") -> int:
    from .audio import record_until_enter
    from .codex_adapter import run_codex
    from .stt import transcribe_audio
    from .tts import speak_text

    audio_path = config.root_dir / "logs" / "last-input.wav"
    response_path = config.root_dir / "logs" / "last-codex-response.md"

    record_until_enter(config.audio, audio_path)
    transcript = transcribe_audio(config.stt, audio_path)
    print(f"\nTranscript:\n{transcript}\n")

    answer = run_codex(transcript, config.codex, response_path)
    print(f"\nCodex answer:\n{answer}\n")

    spoken = trim_for_speech(answer, config.codex.max_spoken_chars)
    speak_text(config.tts, spoken)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local voice interface for Codex CLI.")
    parser.add_argument(
        "--config",
        help="Path to config.toml. Defaults to ./config.toml.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Check local dependencies and model files.")
    subparsers.add_parser("record", help="Record microphone audio to logs/last-input.wav.")

    speak = subparsers.add_parser("speak", help="Speak text with local Piper TTS.")
    speak.add_argument("text")

    subparsers.add_parser("ask", help="Record a command, send it to Codex, speak the answer.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_app_config(args.config)

    try:
        if args.command == "check":
            return command_check(config)
        if args.command == "record":
            return command_record(config)
        if args.command == "speak":
            return command_speak(config, args.text)
        if args.command == "ask":
            return command_ask(config)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
