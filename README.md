# Voice Codex Assistant

Local voice interface for Codex CLI.

The MVP flow is:

```text
record voice -> local STT -> codex exec -> local Piper TTS
```

The assistant can accept Russian or English input, but the default spoken reply voice is English.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
pip install piper-tts
cp config.example.toml config.toml
python scripts/download_piper_voice.py
```

## Check

```bash
voice-codex check
```

## Audio Devices

```bash
voice-codex devices
```

## Speak Test

```bash
voice-codex speak "Hello. Codex voice assistant is ready."
```

## Ask Codex By Voice

```bash
voice-codex ask
```

Press Enter to start recording, speak, then press Enter again to stop.

For a timed recording:

```bash
voice-codex record --duration 5
afplay logs/last-input.wav
```

## Transcribe Test

```bash
voice-codex transcribe logs/last-input.wav
```

If no file is provided, the command uses `logs/last-input.wav`.

## Notes

- STT and TTS run locally.
- Codex CLI may still use a cloud model unless you configure Codex with a local provider.
- The default Piper voice is `en_US-lessac-medium`.
- The default STT language is empty, so Whisper can auto-detect Russian or English.
