from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .config import AudioConfig, WakeWordConfig


@dataclass(frozen=True)
class WakeDetection:
    model_name: str
    score: float


def _suppress_openwakeword_warning() -> None:
    warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")
    try:
        from urllib3.exceptions import NotOpenSSLWarning

        warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
    except Exception:
        pass


def _model_paths(config: WakeWordConfig) -> List[str]:
    paths = [str(path) for path in config.custom_model_paths]
    for name in config.model_names:
        model_path = config.models_dir / f"{name}.{config.inference_framework}"
        if not model_path.exists():
            raise FileNotFoundError(
                f"Wake word model not found: {model_path}. "
                "Run `python scripts/download_openwakeword_models.py`."
            )
        paths.append(str(model_path))
    return paths


def _load_model(config: WakeWordConfig):
    _suppress_openwakeword_warning()
    from openwakeword.model import Model

    return Model(
        wakeword_models=_model_paths(config),
        inference_framework=config.inference_framework,
        melspec_model_path=str(config.models_dir / f"melspectrogram.{config.inference_framework}"),
        embedding_model_path=str(config.models_dir / f"embedding_model.{config.inference_framework}"),
    )


def _best_detection(predictions: Dict[str, float], threshold: float) -> Optional[WakeDetection]:
    if not predictions:
        return None
    model_name, score = max(predictions.items(), key=lambda item: item[1])
    if score >= threshold:
        return WakeDetection(model_name=model_name, score=float(score))
    return None


def wait_for_wake_word(
    audio_config: AudioConfig,
    wake_config: WakeWordConfig,
    timeout_seconds: Optional[float] = None,
) -> WakeDetection:
    if audio_config.sample_rate != 16000:
        raise ValueError("openWakeWord listening currently requires a 16000 Hz sample rate.")
    if audio_config.channels != 1:
        raise ValueError("openWakeWord listening currently requires mono audio.")

    model = _load_model(wake_config)
    timeout = wake_config.timeout_seconds if timeout_seconds is None else timeout_seconds
    deadline = time.monotonic() + timeout if timeout and timeout > 0 else None
    last_detection = 0.0

    print(
        "Listening for wake phrase: "
        + ", ".join(f'"{phrase}"' for phrase in wake_config.wake_phrases)
    )
    print("Active model(s): " + ", ".join(wake_config.model_names))

    try:
        with sd.InputStream(
            samplerate=audio_config.sample_rate,
            channels=audio_config.channels,
            blocksize=wake_config.chunk_samples,
            device=audio_config.recording_device or None,
            dtype="int16",
        ) as stream:
            while True:
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError("Wake word was not detected before timeout.")

                chunk, overflowed = stream.read(wake_config.chunk_samples)
                if overflowed:
                    print("Audio warning: input overflow")

                audio = chunk.reshape(-1).astype(np.int16)
                predictions = model.predict(
                    audio,
                    threshold={name: wake_config.threshold for name in wake_config.model_names},
                    debounce_time=wake_config.debounce_seconds,
                )
                detection = _best_detection(predictions, wake_config.threshold)
                if detection and time.monotonic() - last_detection >= wake_config.debounce_seconds:
                    return detection
    except sd.PortAudioError as exc:
        raise RuntimeError(
            "Could not listen from the microphone. Check macOS microphone permission "
            "and verify the input device with `voice-codex devices`."
        ) from exc


def predict_wake_word_file(wake_config: WakeWordConfig, audio_path: Path) -> WakeDetection:
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = _load_model(wake_config)
    audio, sample_rate = sf.read(str(audio_path), dtype="int16")
    if sample_rate != 16000:
        raise ValueError("Wake-test audio must be 16000 Hz.")
    if len(audio.shape) > 1:
        audio = audio[:, 0]

    predictions = model.predict_clip(audio.astype(np.int16), padding=1, chunk_size=wake_config.chunk_samples)
    best = WakeDetection(model_name="", score=0.0)
    for frame in predictions:
        detection = _best_detection(frame, 0.0)
        if detection and detection.score > best.score:
            best = detection

    if best.score < wake_config.threshold:
        raise RuntimeError(
            f"Wake word not detected. Best score: {best.model_name}={best.score:.3f}; "
            f"threshold={wake_config.threshold:.3f}"
        )

    return best
