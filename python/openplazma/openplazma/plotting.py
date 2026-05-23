from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .signals import validate_signal_series


def _within_range(time_value: float, time_range: Sequence[float] | None) -> bool:
    if time_range is None:
        return True
    if len(time_range) != 2:
        raise ValueError("time_range must contain exactly two values.")
    start, end = float(time_range[0]), float(time_range[1])
    return start <= time_value <= end


def plot_signal(
    signal: dict[str, Any],
    time_range: Sequence[float] | None = None,
    markers: Sequence[float] | None = None,
):
    validated = validate_signal_series(signal)
    import matplotlib.pyplot as plt

    pairs = [
        (time_value, value)
        for time_value, value in zip(validated["time"], validated["values"], strict=True)
        if _within_range(float(time_value), time_range)
    ]
    if len(pairs) == 0:
        raise ValueError("No signal samples are inside the requested time_range.")

    times = [pair[0] for pair in pairs]
    values = [pair[1] for pair in pairs]
    figure, axis = plt.subplots()
    axis.plot(times, values, marker="o")
    axis.set_title(validated["label"])
    axis.set_xlabel(f"time ({validated['timeUnit']})")
    axis.set_ylabel(f"{validated['quantity']} ({validated['unit']})")
    axis.grid(True, alpha=0.3)

    for marker in markers or []:
        axis.axvline(float(marker), color="tab:red", linestyle="--", alpha=0.6)

    return figure
