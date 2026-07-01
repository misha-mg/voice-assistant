from __future__ import annotations

import queue
import time
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .config import AudioConfig


def list_audio_devices() -> str:
    return str(sd.query_devices())


def _device(config: AudioConfig) -> Optional[str]:
    return config.recording_device or None


def _write_audio(output_path: Path, audio: np.ndarray, sample_rate: int) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, sample_rate)
    print(f"Recorded audio: {output_path}")
    return output_path


def _microphone_error(exc: Exception) -> RuntimeError:
    _ = exc
    return RuntimeError(
        "Could not record from the microphone. Check macOS microphone permission "
        "for your terminal app and verify the input device with `voice-codex devices`."
    )


def record_until_enter(config: AudioConfig, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frame_count, time_info, status) -> None:
        if status:
            print(f"Audio warning: {status}")
        frames.put(indata.copy())

    device = _device(config)
    print("Press Enter to start recording.")
    input()
    print("Recording. Press Enter to stop.")

    try:
        with sd.InputStream(
            samplerate=config.sample_rate,
            channels=config.channels,
            device=device,
            dtype="float32",
            callback=callback,
        ):
            input()
    except sd.PortAudioError as exc:
        raise _microphone_error(exc) from exc

    chunks = []
    while not frames.empty():
        chunks.append(frames.get())

    if not chunks:
        raise RuntimeError("No audio was recorded.")

    return _write_audio(output_path, np.concatenate(chunks, axis=0), config.sample_rate)


def record_for_seconds(config: AudioConfig, output_path: Path, duration: float) -> Path:
    if duration <= 0:
        raise ValueError("Duration must be greater than zero.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(config.sample_rate * duration)
    print(f"Recording for {duration:.1f} seconds.")

    try:
        audio = sd.rec(
            frames,
            samplerate=config.sample_rate,
            channels=config.channels,
            device=_device(config),
            dtype="float32",
        )
        sd.wait()
    except sd.PortAudioError as exc:
        raise _microphone_error(exc) from exc

    # A tiny pause helps macOS finish releasing the input device before playback tests.
    time.sleep(0.1)
    return _write_audio(output_path, audio, config.sample_rate)
