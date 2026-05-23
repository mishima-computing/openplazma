from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CONTEXT = REPO_ROOT / "notebooks" / "examples" / "sample-experiment-context.json"
SOURCE_RECORD = REPO_ROOT / "data" / "fixtures" / "static" / "sample-001" / "study-record.json"
TARGET_CONTEXT = REPO_ROOT / "apps" / "workbench-lite" / "files" / "openplazma" / "sample-experiment-context.json"
TARGET_SIGNAL = REPO_ROOT / "apps" / "workbench-lite" / "files" / "openplazma" / "signals" / "plasma_current.json"


def write_json_if_changed(path: Path, value: dict[str, Any]) -> bool:
    rendered = f"{json.dumps(value, indent=2)}\n"
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return True


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return loaded


def sample_signal(record: dict[str, Any]) -> dict[str, Any]:
    for signal in record["signals"]:
        if signal["signalId"] == "plasma-current":
            return signal
    raise ValueError("Fixture record is missing plasma-current signal.")


def main() -> int:
    context_changed = write_json_if_changed(TARGET_CONTEXT, load_json(SOURCE_CONTEXT))
    signal_changed = write_json_if_changed(TARGET_SIGNAL, sample_signal(load_json(SOURCE_RECORD)))
    changed = [name for name, did_change in [("context", context_changed), ("signal", signal_changed)] if did_change]
    if changed:
        print(f"Updated Workbench Lite files: {', '.join(changed)}.")
    else:
        print("Workbench Lite files are already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
