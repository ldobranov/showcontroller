import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT_DIR / "VERSION"


def find_git_root():
    candidates = [
        ROOT_DIR,
        Path.home() / "showcontroller",
    ]

    for path in candidates:
        if (path / ".git").exists():
            return path

    return ROOT_DIR


GIT_ROOT = find_git_root()


def read_version():
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return "unknown"


def git_output(args, default="unknown"):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=GIT_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode != 0:
            return default

        output = result.stdout.strip()
        return output if output else default
    except Exception:
        return default


def get_version_info():
    has_git = (GIT_ROOT / ".git").exists()

    return {
        "version": read_version(),
        "branch": git_output(["branch", "--show-current"]) if has_git else "release",
        "commit": git_output(["rev-parse", "--short", "HEAD"]) if has_git else "package",
        "dirty": git_output(["status", "--porcelain"], default="") != "" if has_git else False,
    }


def get_version():
    return read_version()
