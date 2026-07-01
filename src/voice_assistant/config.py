from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10 fallback
    try:
        import tomli as tomllib
    except ModuleNotFoundError:  # pragma: no cover - setup-free fallback
        tomllib = None


@dataclass(frozen=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    recording_device: str = ""


@dataclass(frozen=True)
class SttConfig:
    engine: str = "faster-whisper"
    model: str = "small"
    language: str = ""
    compute_type: str = "float32"


@dataclass(frozen=True)
class VadConfig:
    enabled: bool = False
    threshold: float = 0.5
    min_silence_duration_ms: int = 700
    speech_pad_ms: int = 100
    max_recording_seconds: float = 20.0


@dataclass(frozen=True)
class WakeWordConfig:
    enabled: bool = False
    inference_framework: str = "onnx"
    models_dir: Path = Path("models/openwakeword")
    model_names: List[str] = None
    custom_model_paths: List[Path] = None
    wake_phrases: List[str] = None
    threshold: float = 0.5
    chunk_samples: int = 1280
    debounce_seconds: float = 1.0
    timeout_seconds: float = 0.0
    acknowledgement: str = "Yes sir. How can I help you?"


@dataclass(frozen=True)
class CodexConfig:
    project_dir: Path
    model: str = "gpt-5.5"
    model_reasoning_effort: str = "low"
    sandbox: str = "workspace-write"
    approval_policy: str = "never"
    skip_git_repo_check: bool = True
    spoken_response_language: str = "English"
    max_spoken_chars: int = 1200


@dataclass(frozen=True)
class TtsConfig:
    voice_model: Path
    voice_config: Path
    output_wav: Path
    engine: str = "piper"
    player: str = "afplay"


@dataclass(frozen=True)
class AppConfig:
    root_dir: Path
    audio: AudioConfig
    vad: VadConfig
    wake_word: WakeWordConfig
    stt: SttConfig
    codex: CodexConfig
    tts: TtsConfig


def _section(data: Dict[str, Any], name: str) -> Dict[str, Any]:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


def _path(root_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root_dir / path


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in inner.split(",")]
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _load_toml(path: Path) -> Dict[str, Any]:
    if tomllib is not None:
        with path.open("rb") as file:
            return tomllib.load(file)

    data: Dict[str, Any] = {}
    current: Dict[str, Any] = data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            current = data.setdefault(section_name, {})
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip()] = _parse_scalar(value)
    return data


def load_config(config_path: Path) -> AppConfig:
    root_dir = config_path.resolve().parent
    if config_path.exists():
        data = _load_toml(config_path)
    else:
        data = {}

    audio = _section(data, "audio")
    vad = _section(data, "vad")
    wake_word = _section(data, "wake_word")
    stt = _section(data, "stt")
    codex = _section(data, "codex")
    tts = _section(data, "tts")

    project_dir = _path(
        root_dir,
        str(codex.get("project_dir") or root_dir),
    )

    return AppConfig(
        root_dir=root_dir,
        audio=AudioConfig(
            sample_rate=int(audio.get("sample_rate", 16000)),
            channels=int(audio.get("channels", 1)),
            recording_device=str(audio.get("recording_device", "")),
        ),
        vad=VadConfig(
            enabled=bool(vad.get("enabled", False)),
            threshold=float(vad.get("threshold", 0.5)),
            min_silence_duration_ms=int(vad.get("min_silence_duration_ms", 700)),
            speech_pad_ms=int(vad.get("speech_pad_ms", 100)),
            max_recording_seconds=float(vad.get("max_recording_seconds", 20.0)),
        ),
        wake_word=WakeWordConfig(
            enabled=bool(wake_word.get("enabled", False)),
            inference_framework=str(wake_word.get("inference_framework", "onnx")),
            models_dir=_path(root_dir, str(wake_word.get("models_dir", "models/openwakeword"))),
            model_names=[
                str(item) for item in wake_word.get("model_names", ["hey_jarvis_v0.1"])
            ],
            custom_model_paths=[
                _path(root_dir, str(item)) for item in wake_word.get("custom_model_paths", [])
            ],
            wake_phrases=[
                str(item)
                for item in wake_word.get(
                    "wake_phrases",
                    [
                        "hey jarvis",
                        "good morning jarvis",
                        "good evening jarvis",
                        "good afternoon jarvis",
                        "hello jarvis",
                    ],
                )
            ],
            threshold=float(wake_word.get("threshold", 0.5)),
            chunk_samples=int(wake_word.get("chunk_samples", 1280)),
            debounce_seconds=float(wake_word.get("debounce_seconds", 1.0)),
            timeout_seconds=float(wake_word.get("timeout_seconds", 0.0)),
            acknowledgement=str(
                wake_word.get("acknowledgement", "Yes sir. How can I help you?")
            ),
        ),
        stt=SttConfig(
            engine=str(stt.get("engine", "faster-whisper")),
            model=str(stt.get("model", "small")),
            language=str(stt.get("language", "")),
            compute_type=str(stt.get("compute_type", "float32")),
        ),
        codex=CodexConfig(
            project_dir=project_dir,
            model=str(codex.get("model", "gpt-5.5")),
            model_reasoning_effort=str(codex.get("model_reasoning_effort", "low")),
            sandbox=str(codex.get("sandbox", "workspace-write")),
            approval_policy=str(codex.get("approval_policy", "never")),
            skip_git_repo_check=bool(codex.get("skip_git_repo_check", True)),
            spoken_response_language=str(
                codex.get("spoken_response_language", "English")
            ),
            max_spoken_chars=int(codex.get("max_spoken_chars", 1200)),
        ),
        tts=TtsConfig(
            engine=str(tts.get("engine", "piper")),
            voice_model=_path(
                root_dir,
                str(tts.get("voice_model", "models/piper/en_US-lessac-medium.onnx")),
            ),
            voice_config=_path(
                root_dir,
                str(tts.get("voice_config", "models/piper/en_US-lessac-medium.onnx.json")),
            ),
            output_wav=_path(root_dir, str(tts.get("output_wav", "logs/last-response.wav"))),
            player=str(tts.get("player", "afplay")),
        ),
    )
