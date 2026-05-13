import subprocess
from pathlib import Path

from .config import WORKDIR


def run_bash(command: str, cwd: Path | None = None) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Dangerous command, please do not run it."
    try:
        r = subprocess.run(command, shell=True, cwd=str(cwd or WORKDIR), capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "Command output is empty."
    except subprocess.TimeoutExpired:
        return "Command timeout."
    except Exception as e:
        return "Command error: " + str(e)


def safe_path(p: str, base_dir: Path | None = None) -> Path:
    root = (base_dir or WORKDIR).resolve()
    path = (root / p).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path {p} is outside the working directory.")
    return path


def run_read(path: str, limit: int = None, base_dir: Path | None = None) -> str:
    try:
        text = safe_path(path, base_dir=base_dir).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"...({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str, base_dir: Path | None = None) -> str:
    try:
        fp = safe_path(path, base_dir=base_dir)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error:{e}"


def run_edit(path: str, old_text: str, new_text: str, base_dir: Path | None = None) -> str:
    try:
        fp = safe_path(path, base_dir=base_dir)
        content = fp.read_text()
        if old_text not in content:
            return f"Error:text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error {e}"
