from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path


FORBIDDEN_PATH_PARTS = [
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".vite",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "_output",
    ".cache",
    ".openplazma",
]

FORBIDDEN_PATH_SUFFIXES = [
    ".egg-info",
]

FORBIDDEN_GENERATED_FILE_PATTERNS = [
    "openplazma-*.png",
    "openplazma-real-signal-room-*.png",
    "*.tgz",
    ".jupyterlite.doit.db",
]

SECRET_PATTERNS = [
    "OPENAI" + "_API_KEY",
    "s" + "k-",
    "ghp" + "_",
    "github" + "_pat_",
    "BEGIN" + " PRIVATE KEY",
    "AWS" + "_SECRET_ACCESS_KEY",
    "password" + "=",
    "secret" + "=",
    "token" + "=",
]


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        text=True,
        capture_output=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def path_reasons(filename: str) -> list[str]:
    path = Path(filename)
    normalized_parts = set(path.parts)
    reasons: list[str] = []

    for part in FORBIDDEN_PATH_PARTS:
        if part in normalized_parts:
            reasons.append(f"tracked generated or local directory: {part}/")

    for suffix in FORBIDDEN_PATH_SUFFIXES:
        if any(path_part.endswith(suffix) for path_part in path.parts):
            reasons.append(f"tracked generated metadata directory: *{suffix}/")

    basename = path.name
    for pattern in FORBIDDEN_GENERATED_FILE_PATTERNS:
        if fnmatch.fnmatch(basename, pattern):
            reasons.append(f"tracked generated file: {pattern}")

    return reasons


def secret_reasons(filename: str) -> list[str]:
    path = Path(filename)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    reasons: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for pattern in SECRET_PATTERNS:
            if pattern in line:
                reasons.append(f"secret-like pattern '{pattern}' at line {line_number}")
    return reasons


def main() -> int:
    failures: list[str] = []

    for filename in tracked_files():
        for reason in path_reasons(filename):
            failures.append(f"{filename}: {reason}")
        for reason in secret_reasons(filename):
            failures.append(f"{filename}: {reason}")

    if failures:
        print("Public repository hygiene check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Public repository hygiene check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
