from __future__ import annotations

from pathlib import Path

from .config import SttConfig


def transcribe_audio(config: SttConfig, audio_path: Path) -> str:
    if config.engine != "faster-whisper":
        raise ValueError(f"Unsupported STT engine: {config.engine}")

    from faster_whisper import WhisperModel

    language = config.language or None
    model = WhisperModel(config.model, compute_type=config.compute_type)
    segments, info = model.transcribe(str(audio_path), language=language, vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments).strip()

    detected = getattr(info, "language", None)
    if detected:
        print(f"Detected language: {detected}")

    if not text:
        raise RuntimeError("STT returned empty text.")

    return text
