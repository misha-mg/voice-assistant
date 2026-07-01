from __future__ import annotations

import subprocess
from pathlib import Path

from .commands import find_executable
from .config import CodexConfig


def build_voice_prompt(command: str, config: CodexConfig) -> str:
    return f"""You are responding through a voice assistant.

The text below is a transcript of the user's spoken request. It may be a
task, a short command, a question, or an explanation of what the user wants.
Treat it as the user's actual request, even though it arrives without other
conversation context.

User's spoken request:

{command}

Execute the user's request in the current project.

For your final answer:
- reply in {config.spoken_response_language};
- write in a natural human voice because the answer will be read aloud;
- keep the answer to three sentences or fewer by default;
- prefer a very short acknowledgement when the task is simple, for example
  "Yes, I started the project.", "Yes, I turned on the music.", or
  "No, that is not correct.";
- give a longer explanation only when the user asks you to explain,
  analyze, compare, or teach something;
- mention changed files or commands run only when relevant;
- do not include code blocks unless the user explicitly asked for code;
- do not add English-learning corrections, grammar tips, or meta commentary
  unless the spoken request explicitly asks for them.
"""


def run_codex(command: str, config: CodexConfig, output_path: Path) -> str:
    codex = find_executable("codex")
    if not codex:
        raise FileNotFoundError("Codex CLI not found. Install and authenticate Codex first.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    args = [
        codex,
        "exec",
    ]
    if config.skip_git_repo_check:
        args.append("--skip-git-repo-check")
    args.extend(
        [
            "-m",
            config.model,
            "-c",
            f'model_reasoning_effort="{config.model_reasoning_effort}"',
            "-C",
            str(config.project_dir),
            "-s",
            config.sandbox,
            "--output-last-message",
            str(output_path),
            "-",
        ]
    )

    prompt = build_voice_prompt(command, config)
    print("Sending command to Codex CLI...")
    result = subprocess.run(
        args,
        input=prompt,
        text=True,
        capture_output=True,
        cwd=str(config.project_dir),
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Codex failed with exit code {result.returncode}: {message}")

    if output_path.exists():
        answer = output_path.read_text(encoding="utf-8").strip()
    else:
        answer = result.stdout.strip()

    if not answer:
        raise RuntimeError("Codex returned an empty answer.")

    return answer
