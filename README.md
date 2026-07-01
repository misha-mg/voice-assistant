# Voice Codex Assistant

Local voice interface for Codex CLI with local STT, local TTS, VAD auto-stop recording, and wake phrase detection.

The main flow is:

```text
wake phrase -> acknowledgement -> record command -> local STT -> Codex CLI -> local TTS
```

The assistant accepts English or Russian speech input. Replies are spoken with an English Piper voice.

## Features

- Local speech-to-text with `faster-whisper`
- Local text-to-speech with Piper
- Auto-stop command recording with Silero VAD
- Wake phrase detection with openWakeWord
- Active wake phrase: `hey jarvis`
- Wake acknowledgement: `Yes sir. How can I help you?`
- Codex CLI execution with `gpt-5.5` and `model_reasoning_effort = "low"`
- Temporary audio/response files only; no permanent response logging by default

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
cp config.example.toml config.toml
python scripts/download_piper_voice.py
python scripts/download_openwakeword_models.py
```

Codex CLI must also be installed and authenticated:

```bash
codex --version
codex login
```

## Check Environment

```bash
voice-codex check
```

This verifies Codex CLI, Piper, the audio player, Piper voice files, and openWakeWord model files.

## Continuous Wake Flow

Start the continuous assistant:

```bash
voice-codex listen
```

The assistant keeps running after each answer and returns to wake phrase listening. Stop it with `Ctrl+C`.

## One-Shot Wake Flow

Run one wake-triggered command:

```bash
voice-codex listen --once
```

Then say:

```text
hey jarvis
```

The assistant should reply:

```text
Yes sir. How can I help you?
```

After the acknowledgement finishes, speak your command. For example:

```text
Summarize this project in one short sentence without changing any files.
```

Expected terminal states:

```text
[listening]
Wake detected
[speaking]
Speak your command.
[recording]
[transcribing]
[thinking]
[speaking]
[idle]
[listening]
```

## Useful Commands

List audio devices:

```bash
voice-codex devices
```

Speak a test phrase:

```bash
voice-codex speak "Hello sir. How can I help you?"
```

Record with manual stop:

```bash
voice-codex record
```

Record for a fixed duration:

```bash
voice-codex record --duration 5
afplay logs/last-input.wav
```

Record until VAD detects the end of speech:

```bash
voice-codex record --vad
afplay logs/last-input.wav
```

Transcribe a recorded file:

```bash
voice-codex transcribe logs/last-input.wav
```

Ask Codex with typed text:

```bash
voice-codex ask-text "Summarize this project in one short sentence without changing any files."
```

Run the full flow without the wake phrase:

```bash
voice-codex ask --vad
```

Run the full flow from an existing WAV file:

```bash
voice-codex ask --audio-path logs/last-input.wav
```

Test wake phrase detection from a 16 kHz mono WAV file:

```bash
voice-codex wake-test logs/hey-jarvis-test.wav
```

## Wake Phrases

The active pretrained wake phrase is:

```text
hey jarvis
```

The config also lists desired future phrases:

```text
good morning jarvis
good evening jarvis
good afternoon jarvis
hello jarvis
```

Those additional phrases need their own openWakeWord ONNX models before they can trigger reliably. Add custom model paths in `config.toml` under `wake_word.custom_model_paths`.

## Configuration

Main config file:

```text
config.toml
```

Important defaults:

```toml
[codex]
model = "gpt-5.5"
model_reasoning_effort = "low"

[wake_word]
model_names = ["hey_jarvis_v0.1"]
acknowledgement = "Yes sir. How can I help you?"

[tts]
voice_model = "models/piper/en_US-lessac-medium.onnx"

[vad]
max_recording_seconds = 20.0
```

## Temporary Files

Runtime files are written under `logs/` and ignored by Git:

- `logs/last-input.wav`
- `logs/last-response.wav`
- `logs/last-codex-response.md`

These files are overwritten during normal use and are not treated as permanent logs.

## Troubleshooting

If microphone recording fails, check macOS microphone permissions for your terminal app and run:

```bash
voice-codex devices
```

If TTS fails, run:

```bash
python scripts/download_piper_voice.py
voice-codex check
```

If wake detection fails, run:

```bash
python scripts/download_openwakeword_models.py
voice-codex check
```

If Codex is slow, confirm the project config uses:

```toml
model = "gpt-5.5"
model_reasoning_effort = "low"
```

## Limitations

- Only `hey jarvis` has an active pretrained wake phrase model.
- Additional Jarvis phrases need custom openWakeWord ONNX models.
- STT can misrecognize filenames, package names, and shell commands.
- The Safety Confirmation Layer is postponed and should be added before risky command execution.
- Codex itself may still use cloud inference unless you configure Codex with a local provider.
