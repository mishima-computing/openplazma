from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any


LOCAL_STORAGE_KEY = "openplazma.experimentContext.v0"


def _decode_base64url(value: str) -> dict[str, Any]:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
    loaded = json.loads(decoded.decode("utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Decoded opContext must be a JSON object.")
    return loaded


def load_context_from_query() -> dict[str, Any] | None:
    try:
        from js import URLSearchParams, window
    except ImportError:
        return None

    params = URLSearchParams.new(window.location.search)
    encoded = params.get("opContext")
    if not encoded:
        return None
    return _decode_base64url(str(encoded))


def load_context_from_local_storage() -> dict[str, Any] | None:
    try:
        from js import window
    except ImportError:
        return None

    stored = window.localStorage.getItem(LOCAL_STORAGE_KEY)
    if not stored:
        return None
    loaded = json.loads(str(stored))
    if not isinstance(loaded, dict):
        raise ValueError("Stored ExperimentContext must be a JSON object.")
    return loaded


def load_context_from_file(path: str | Path = "sample-experiment-context.json") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError("ExperimentContext file must contain a JSON object.")
    return loaded


def load_context(path: str | Path = "sample-experiment-context.json") -> dict[str, Any]:
    return load_context_from_query() or load_context_from_local_storage() or load_context_from_file(path)


def load_signal(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError("Signal file must contain a JSON object.")
    for field in ["signalId", "label", "quantity", "unit", "timeUnit", "time", "values"]:
        if field not in loaded:
            raise ValueError(f"Signal is missing required field: {field}")
    if len(loaded["time"]) != len(loaded["values"]):
        raise ValueError("Signal time and values arrays must have matching lengths.")
    return loaded


def _inside_range(time_value: float, time_range: list[float] | tuple[float, float] | None) -> bool:
    if time_range is None:
        return True
    if len(time_range) != 2:
        raise ValueError("time_range must contain exactly two values.")
    start, end = float(time_range[0]), float(time_range[1])
    return start <= time_value <= end


def plot_signal(signal: dict[str, Any], time_range: list[float] | tuple[float, float] | None = None):
    import matplotlib.pyplot as plt

    pairs = [
        (float(time_value), float(value))
        for time_value, value in zip(signal["time"], signal["values"], strict=True)
        if _inside_range(float(time_value), time_range)
    ]
    if not pairs:
        raise ValueError("No signal samples are inside the requested time_range.")

    times = [pair[0] for pair in pairs]
    values = [pair[1] for pair in pairs]
    figure, axis = plt.subplots()
    axis.plot(times, values, marker="o")
    axis.set_title(signal["label"])
    axis.set_xlabel(f"time ({signal['timeUnit']})")
    axis.set_ylabel(f"{signal['quantity']} ({signal['unit']})")
    axis.grid(True, alpha=0.3)
    return figure
