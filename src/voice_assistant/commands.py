from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Optional


def find_executable(name: str) -> Optional[str]:
    path = shutil.which(name)
    if path:
        return path

    for directory in [Path(sys.executable).parent, Path(sys.prefix) / "bin"]:
        local_path = directory / name
        if local_path.exists() and local_path.is_file():
            return str(local_path)

    return None
