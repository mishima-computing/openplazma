from __future__ import annotations

import math
from typing import Any

from ._validation import require_keys, require_number_list, require_string


def validate_signal_series(signal: dict[str, Any]) -> dict[str, Any]:
    require_keys(signal, ["kind", "version", "signalId", "label", "quantity", "unit", "timeUnit", "time", "values"], "SignalSeries")
    if signal["kind"] != "openplazma.signal_series":
        raise ValueError("SignalSeries.kind must be openplazma.signal_series.")
    if signal["version"] != "0.1.0":
        raise ValueError("SignalSeries.version must be 0.1.0.")
    require_string(signal["signalId"], "SignalSeries.signalId")
    require_string(signal["label"], "SignalSeries.label")
    require_string(signal["quantity"], "SignalSeries.quantity")
    require_string(signal["unit"], "SignalSeries.unit")
    if signal["timeUnit"] != "s":
        raise ValueError("SignalSeries.timeUnit must be 's'.")

    time = require_number_list(signal["time"], "SignalSeries.time")
    values = require_number_list(signal["values"], "SignalSeries.values")
    if len(time) == 0:
        raise ValueError("SignalSeries.time must include at least one sample.")
    if len(time) != len(values):
        raise ValueError("SignalSeries.time and SignalSeries.values must have matching lengths.")
    if not all(math.isfinite(value) for value in [*time, *values]):
        raise ValueError("SignalSeries.time and SignalSeries.values must contain only finite numbers.")

    for index in range(1, len(time)):
        if time[index] <= time[index - 1]:
            raise ValueError("SignalSeries.time values must be strictly increasing.")

    return signal


def summarize_signal(signal: dict[str, Any]) -> dict[str, float | int]:
    validated = validate_signal_series(signal)
    values = validated["values"]
    return {
        "point_count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }
