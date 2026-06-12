from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}.")


def loads_json(value: str) -> Any:
    return json.loads(value, parse_constant=_reject_json_constant)


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        value = json.load(file, parse_constant=_reject_json_constant)

    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object at {path}.")

    return value


def save_json(value: dict[str, Any], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = json.dumps(value, indent=2, allow_nan=False)
    except TypeError as error:
        raise ValueError("JSON value must be serializable.") from error
    except ValueError as error:
        raise ValueError("JSON value must not contain NaN or Infinity.") from error
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(f"{text}\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
