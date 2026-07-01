from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from .commands import find_executable
from .runtime import runtime_state, show_state

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
        ("codex", find_executable("codex")),
        ("piper", find_executable("piper")),
        (config.tts.player, find_executable(config.tts.player)),
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
        ("Wake word models dir", config.wake_word.models_dir),
        ("Codex project dir", config.codex.project_dir),
    ]:
        if path.exists():
            print(f"OK: {label} -> {path}")
        else:
            ok = False
            print(f"Missing: {label} -> {path}")

    for filename in [
        f"embedding_model.{config.wake_word.inference_framework}",
        f"melspectrogram.{config.wake_word.inference_framework}",
        *[
            f"{name}.{config.wake_word.inference_framework}"
            for name in config.wake_word.model_names
        ],
    ]:
        path = config.wake_word.models_dir / filename
        if path.exists():
            print(f"OK: Wake word file -> {path}")
        else:
            ok = False
            print(f"Missing: Wake word file -> {path}")

    return 0 if ok else 1


def command_wake_test(config: "AppConfig", audio_path: str) -> int:
    from .wake_word import predict_wake_word_file

    path = Path(audio_path).expanduser()
    if not path.is_absolute():
        path = config.root_dir / path
    with runtime_state("listening", str(path)):
        detection = predict_wake_word_file(config.wake_word, path)
    print(f"Wake detected: {detection.model_name} score={detection.score:.3f}")
    show_state("idle")
    return 0


def command_devices() -> int:
    from .audio import list_audio_devices

    print(list_audio_devices())
    return 0


def command_record(config: "AppConfig", duration: Optional[float], use_vad: bool) -> int:
    from .audio import record_for_seconds, record_until_enter, record_until_silence

    audio_path = config.root_dir / "logs" / "last-input.wav"
    with runtime_state("recording"):
        if use_vad or config.vad.enabled:
            record_until_silence(config.audio, config.vad, audio_path)
        elif duration is None:
            record_until_enter(config.audio, audio_path)
        else:
            record_for_seconds(config.audio, audio_path, duration)
    show_state("idle")
    return 0


def command_speak(config: "AppConfig", text: str) -> int:
    from .tts import speak_text

    with runtime_state("speaking"):
        speak_text(config.tts, text)
    show_state("idle")
    return 0


def command_transcribe(config: "AppConfig", audio_path: Optional[str]) -> int:
    from .stt import transcribe_audio

    path = Path(audio_path).expanduser() if audio_path else config.root_dir / "logs" / "last-input.wav"
    if not path.is_absolute():
        path = config.root_dir / path
    with runtime_state("transcribing", str(path)):
        transcript = transcribe_audio(config.stt, path)
    print(transcript)
    show_state("idle")
    return 0


def command_ask_text(config: "AppConfig", text: str) -> int:
    from .codex_adapter import run_codex

    response_path = config.root_dir / "logs" / "last-codex-response.md"
    with runtime_state("thinking"):
        answer = run_codex(text, config.codex, response_path)
    print(answer)
    show_state("idle")
    return 0


def resolve_audio_path(config: "AppConfig", audio_path: Optional[str]) -> Path:
    path = Path(audio_path).expanduser() if audio_path else config.root_dir / "logs" / "last-input.wav"
    if not path.is_absolute():
        path = config.root_dir / path
    return path


def command_ask(
    config: "AppConfig",
    duration: Optional[float],
    existing_audio_path: Optional[str],
    use_vad: bool,
) -> int:
    from .audio import record_for_seconds, record_until_enter, record_until_silence
    from .codex_adapter import run_codex
    from .stt import transcribe_audio
    from .tts import speak_text

    audio_path = resolve_audio_path(config, existing_audio_path)
    response_path = config.root_dir / "logs" / "last-codex-response.md"

    if existing_audio_path:
        print(f"Using existing audio: {audio_path}")
    elif use_vad or config.vad.enabled:
        with runtime_state("recording"):
            record_until_silence(config.audio, config.vad, audio_path)
    elif duration is None:
        with runtime_state("recording"):
            record_until_enter(config.audio, audio_path)
    else:
        with runtime_state("recording"):
            record_for_seconds(config.audio, audio_path, duration)

    with runtime_state("transcribing", str(audio_path)):
        transcript = transcribe_audio(config.stt, audio_path)
    print(f"\nTranscript:\n{transcript}\n")

    with runtime_state("thinking"):
        answer = run_codex(transcript, config.codex, response_path)
    print(f"\nCodex answer:\n{answer}\n")

    spoken = trim_for_speech(answer, config.codex.max_spoken_chars)
    with runtime_state("speaking"):
        speak_text(config.tts, spoken)
    show_state("idle")
    return 0


def command_listen(config: "AppConfig", once: bool, timeout: Optional[float]) -> int:
    from .tts import speak_text
    from .wake_word import wait_for_wake_word

    while True:
        try:
            with runtime_state("listening"):
                detection = wait_for_wake_word(config.audio, config.wake_word, timeout)
            print(f"Wake detected: {detection.model_name} score={detection.score:.3f}")
            with runtime_state("speaking"):
                speak_text(config.tts, config.wake_word.acknowledgement)
            print("Speak your command.")
            command_ask(config, duration=None, existing_audio_path=None, use_vad=True)
        except Exception as exc:
            show_state("error")
            print(f"Error: {exc}", flush=True)
            if once:
                return 1
            print("Returning to wake phrase listening.", flush=True)
        if once:
            break

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local voice interface for Codex CLI.")
    parser.add_argument(
        "--config",
        help="Path to config.toml. Defaults to ./config.toml.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Check local dependencies and model files.")
    subparsers.add_parser("devices", help="List local audio devices.")

    record = subparsers.add_parser("record", help="Record microphone audio to logs/last-input.wav.")
    record.add_argument(
        "--duration",
        type=float,
        help="Record for this many seconds instead of waiting for Enter to stop.",
    )
    record.add_argument(
        "--vad",
        action="store_true",
        help="Record until VAD detects the end of speech.",
    )

    speak = subparsers.add_parser("speak", help="Speak text with local Piper TTS.")
    speak.add_argument("text")

    transcribe = subparsers.add_parser("transcribe", help="Transcribe a WAV file with local STT.")
    transcribe.add_argument(
        "audio_path",
        nargs="?",
        help="Path to a WAV file. Defaults to logs/last-input.wav.",
    )

    ask_text = subparsers.add_parser("ask-text", help="Send a text command to Codex CLI.")
    ask_text.add_argument("text", help="Text command to send to Codex.")

    wake_test = subparsers.add_parser("wake-test", help="Test wake word detection on a WAV file.")
    wake_test.add_argument("audio_path", help="Path to a 16 kHz mono WAV file.")

    ask = subparsers.add_parser("ask", help="Record a command, send it to Codex, speak the answer.")
    ask.add_argument(
        "--duration",
        type=float,
        help="Record for this many seconds instead of waiting for Enter to stop.",
    )
    ask.add_argument(
        "--audio-path",
        help="Use an existing WAV file instead of recording from the microphone.",
    )
    ask.add_argument(
        "--vad",
        action="store_true",
        help="Record until VAD detects the end of speech.",
    )

    listen = subparsers.add_parser(
        "listen",
        help="Continuously wait for wake phrases and run the voice assistant.",
    )
    listen.add_argument(
        "--once",
        action="store_true",
        help="Stop after one detected wake phrase and command.",
    )
    listen.add_argument(
        "--timeout",
        type=float,
        help="Stop listening if no wake phrase is detected within this many seconds.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_app_config(args.config)

    try:
        if args.command == "check":
            return command_check(config)
        if args.command == "devices":
            return command_devices()
        if args.command == "record":
            return command_record(config, args.duration, args.vad)
        if args.command == "speak":
            return command_speak(config, args.text)
        if args.command == "transcribe":
            return command_transcribe(config, args.audio_path)
        if args.command == "ask-text":
            return command_ask_text(config, args.text)
        if args.command == "wake-test":
            return command_wake_test(config, args.audio_path)
        if args.command == "ask":
            return command_ask(config, args.duration, args.audio_path, args.vad)
        if args.command == "listen":
            return command_listen(config, args.once, args.timeout)
    except KeyboardInterrupt:
        print("\nCancelled.")
        show_state("idle")
        return 130
    except Exception as exc:
        show_state("error")
        print(f"Error: {exc}", flush=True)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
