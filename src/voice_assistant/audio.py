from __future__ import annotations

import queue
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from .config import AudioConfig


def record_until_enter(config: AudioConfig, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frame_count, time_info, status) -> None:
        if status:
            print(f"Audio warning: {status}")
        frames.put(indata.copy())

    device = config.recording_device or None
    print("Press Enter to start recording.")
    input()
    print("Recording. Press Enter to stop.")

    with sd.InputStream(
        samplerate=config.sample_rate,
        channels=config.channels,
        device=device,
        dtype="float32",
        callback=callback,
    ):
        input()

    chunks = []
    while not frames.empty():
        chunks.append(frames.get())

    if not chunks:
        raise RuntimeError("No audio was recorded.")

    audio = np.concatenate(chunks, axis=0)
    sf.write(output_path, audio, config.sample_rate)
    print(f"Recorded audio: {output_path}")
    return output_path
