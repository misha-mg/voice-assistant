from __future__ import annotations

import subprocess
from pathlib import Path

from .config import CodexConfig


def build_voice_prompt(command: str, config: CodexConfig) -> str:
    return f"""You are being controlled through a voice assistant.

The user dictated this command:

{command}

Execute the user's request in the current project.

For your final answer:
- reply in {config.spoken_response_language};
- be concise because the answer will be read aloud;
- mention changed files or commands run when relevant;
- do not include long code blocks unless the user explicitly asked for code.
"""


def run_codex(command: str, config: CodexConfig, output_path: Path) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    args = [
        "codex",
        "exec",
    ]
    if config.skip_git_repo_check:
        args.append("--skip-git-repo-check")
    args.extend(
        [
            "-C",
            str(config.project_dir),
            "-s",
            config.sandbox,
            "-a",
            config.approval_policy,
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
