from __future__ import annotations

import queue
import time
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .config import AudioConfig, VadConfig


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


def record_until_silence(
    audio_config: AudioConfig,
    vad_config: VadConfig,
    output_path: Path,
) -> Path:
    if audio_config.sample_rate != 16000:
        raise ValueError("Silero VAD recording currently requires a 16000 Hz sample rate.")
    if audio_config.channels != 1:
        raise ValueError("Silero VAD recording currently requires mono audio.")
    if vad_config.max_recording_seconds <= 0:
        raise ValueError("VAD max_recording_seconds must be greater than zero.")

    from silero_vad import VADIterator, load_silero_vad
    import torch

    output_path.parent.mkdir(parents=True, exist_ok=True)
    model = load_silero_vad()
    vad_iterator = VADIterator(
        model,
        threshold=vad_config.threshold,
        sampling_rate=audio_config.sample_rate,
        min_silence_duration_ms=vad_config.min_silence_duration_ms,
        speech_pad_ms=vad_config.speech_pad_ms,
    )

    chunk_size = 512
    max_chunks = int(vad_config.max_recording_seconds * audio_config.sample_rate / chunk_size)
    chunks = []
    speech_started = False

    print(
        "Recording with VAD. Speak now; recording stops after silence "
        f"or {vad_config.max_recording_seconds:.1f}s."
    )

    try:
        with sd.InputStream(
            samplerate=audio_config.sample_rate,
            channels=audio_config.channels,
            blocksize=chunk_size,
            device=_device(audio_config),
            dtype="float32",
        ) as stream:
            for _ in range(max_chunks):
                chunk, overflowed = stream.read(chunk_size)
                if overflowed:
                    print("Audio warning: input overflow")

                mono = chunk.reshape(-1).astype(np.float32)
                chunks.append(mono.copy())
                event = vad_iterator(torch.from_numpy(mono), return_seconds=False)

                if event:
                    if "start" in event:
                        speech_started = True
                    if "end" in event and speech_started:
                        break
    except sd.PortAudioError as exc:
        raise _microphone_error(exc) from exc
    finally:
        vad_iterator.reset_states()

    if not chunks:
        raise RuntimeError("No audio was recorded.")
    if not speech_started:
        raise RuntimeError("No speech was detected before the VAD timeout.")

    audio = np.concatenate(chunks, axis=0).reshape(-1, 1)
    time.sleep(0.1)
    return _write_audio(output_path, audio, audio_config.sample_rate)
