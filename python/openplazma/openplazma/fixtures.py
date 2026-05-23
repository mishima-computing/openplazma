from __future__ import annotations

from pathlib import Path
from typing import Any

from .records import load_study_record
from .signals import validate_signal_series


def load_static_signal(repo_root: str | Path, shot_id: str, signal_id: str) -> dict[str, Any]:
    fixture_path = Path(repo_root) / "data" / "fixtures" / "static" / shot_id / "study-record.json"
    record = load_study_record(fixture_path)

    source = record["shot"]["source"]
    if source.get("provider") != "STATIC_FIXTURE":
        raise ValueError("Only STATIC_FIXTURE records can be loaded by load_static_signal.")

    for signal in record["signals"]:
        if signal["signalId"] == signal_id:
            return validate_signal_series(signal)

    raise ValueError(f"Signal '{signal_id}' was not found in static shot '{shot_id}'.")
