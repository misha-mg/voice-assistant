# PRD: Local Voice Assistant for Codex CLI

## 1. Summary

Build a local voice assistant that listens for a wake phrase, acknowledges the user, records a spoken command, transcribes it with a local STT model, sends the text to Codex CLI, receives Codex's final answer, and speaks that answer with a local TTS model.

STT, VAD, wake phrase detection, and TTS run locally. Codex CLI uses the configured Codex model provider. By default this project runs Codex with `gpt-5.5` and `model_reasoning_effort = "low"` for faster responses without downgrading the model.

## 2. Goals

- Provide a voice interface for Codex CLI.
- Keep STT, TTS, VAD, and wake phrase detection local.
- Use an English TTS voice for replies, even when the spoken command is Russian.
- Support `hey jarvis` as the active wake phrase.
- Say an acknowledgement before recording the user's command.
- Avoid permanent response logging by default.
- Keep temporary audio and response files ignored by Git and overwritten during normal use.

## 3. Non-Goals

- Do not replace Codex CLI.
- Do not train custom STT or TTS models in the MVP.
- Do not use cloud STT or TTS APIs.
- Do not build a full GUI in the MVP.
- Do not create extra Git worktrees or duplicate project folders unless explicitly requested.

## 4. Current User Flow

1. The user starts `voice-codex listen`.
2. The assistant listens for the wake phrase.
3. The user says `hey jarvis`.
4. The assistant says: `Yes sir. How can I help you?`
5. After the acknowledgement finishes, the assistant records the user's command.
6. VAD automatically stops recording after speech ends.
7. Local STT transcribes the recorded audio.
8. The transcript is sent to Codex CLI.
9. Codex returns a concise English final answer.
10. The answer is spoken with the local Piper English voice.
11. The assistant returns to wake phrase listening instead of exiting.

## 5. Architecture

```text
Microphone
  -> openWakeWord wake phrase detector
  -> acknowledgement TTS
  -> Silero VAD command recorder
  -> local STT with faster-whisper
  -> Codex CLI adapter
  -> response trimming
  -> local Piper TTS
  -> speaker
```

## 6. Components

### Wake Phrase Detection

Engine: `openwakeword`

Active model:

- `hey_jarvis_v0.1`

Configured desired phrases:

- `hey jarvis`
- `good morning jarvis`
- `good evening jarvis`
- `good afternoon jarvis`
- `hello jarvis`

Only `hey jarvis` is active with a ready pretrained model. The other phrases require custom openWakeWord ONNX models before they can trigger reliably.

### Voice Activity Detection

Engine: `silero-vad`

Purpose:

- Start recording after the wake acknowledgement.
- Stop recording automatically after the user's speech ends.
- Keep manual and timed recording modes as fallbacks.

### STT

Engine: `faster-whisper`

Default model:

- `small`

Default language:

- Empty value, allowing automatic language detection.

The assistant supports English and Russian input. Accuracy can be improved later by switching to `medium` or `large-v3`.

### Codex CLI Adapter

The assistant sends text prompts to `codex exec`.

Default Codex settings:

- Model: `gpt-5.5`
- Reasoning effort: `low`
- Sandbox: `workspace-write`
- Output transfer: temporary `logs/last-codex-response.md`

The temporary response file is overwritten on each run and ignored by Git.

### TTS

Engine: `Piper`

Default voice:

- `en_US-lessac-medium`

The assistant speaks both the wake acknowledgement and Codex replies with this English voice.

## 7. MVP Features

- `voice-codex check`
- `voice-codex devices`
- `voice-codex speak`
- `voice-codex record`
- `voice-codex record --duration N`
- `voice-codex record --vad`
- `voice-codex transcribe [audio_path]`
- `voice-codex ask-text TEXT`
- `voice-codex ask`
- `voice-codex ask --duration N`
- `voice-codex ask --audio-path PATH`
- `voice-codex ask --vad`
- `voice-codex wake-test AUDIO_PATH`
- `voice-codex listen`
- `voice-codex listen --once`
- `voice-codex listen --once --timeout N`

## 8. Runtime States

The assistant prints runtime states in the terminal:

- `listening`
- `recording`
- `transcribing`
- `thinking`
- `speaking`
- `idle`
- `error`

Expected full wake flow:

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

## 9. Safety And Privacy

- Responses are not permanently logged by default.
- Files in `logs/` are temporary ignored files.
- Audio and response files are overwritten during normal use.
- The microphone is not recording commands while the assistant is speaking.
- The Safety Confirmation Layer is postponed and should be revisited before allowing risky commands.

Risky command categories for the postponed safety layer:

- deleting files;
- changing Git history;
- installing packages;
- running privileged commands;
- handling secrets or tokens;
- sending data externally.

## 10. Configuration

The main config lives in `config.toml`.

Important sections:

```toml
[codex]
model = "gpt-5.5"
model_reasoning_effort = "low"

[tts]
voice_model = "models/piper/en_US-lessac-medium.onnx"

[wake_word]
model_names = ["hey_jarvis_v0.1"]
acknowledgement = "Yes sir. How can I help you?"

[vad]
max_recording_seconds = 20.0
```

## 11. Dependencies

Core runtime:

- Python 3.9+
- Codex CLI
- `faster-whisper`
- `sounddevice`
- `soundfile`
- `piper-tts`
- `silero-vad`
- `openwakeword`

Local models:

- Piper voice: `en_US-lessac-medium`
- Whisper model: `small`
- openWakeWord model: `hey_jarvis_v0.1`

## 12. Test Plan

Environment check:

```bash
voice-codex check
```

TTS check:

```bash
voice-codex speak "Yes sir. How can I help you?"
```

VAD recording check:

```bash
voice-codex record --vad
afplay logs/last-input.wav
```

STT check:

```bash
voice-codex transcribe logs/last-input.wav
```

Codex text check:

```bash
voice-codex ask-text "Summarize this project in one short sentence without changing any files."
```

Full voice check without wake phrase:

```bash
voice-codex ask --vad
```

Wake model file check:

```bash
voice-codex wake-test logs/hey-jarvis-test.wav
```

Full wake flow:

```bash
voice-codex listen
```

## 13. Known Limitations

- Only `hey jarvis` has an active pretrained wake phrase model.
- Additional wake phrases need custom ONNX models.
- STT may misrecognize filenames, package names, and shell commands.
- Long Codex answers are trimmed before speech.
- The Safety Confirmation Layer is postponed.
- Codex itself may still use cloud inference unless configured with a local provider.

## 14. Future Work

- Add the postponed Safety Confirmation Layer.
- Train custom openWakeWord models for the additional Jarvis phrases.
- Add dialogue continuation with `codex exec resume --last`.
- Add push-to-talk mode.
- Add optional debug logs without storing all assistant responses.
- Add a small tray UI for macOS.
