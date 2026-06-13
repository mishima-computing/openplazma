from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from ._validation import require_finite_number, require_keys, require_number_list, require_string

_SAMPLE_TOLERANCE = 1e-9


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


def _validated_time_and_values(signal: dict[str, Any]) -> tuple[dict[str, Any], list[float], list[float]]:
    validated = validate_signal_series(signal)
    return validated, [float(value) for value in validated["time"]], [float(value) for value in validated["values"]]


def _time_window_pair(value: Sequence[float] | None, name: str) -> tuple[float, float] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ValueError(f"{name} must be a [start, end] pair.")
    start = require_finite_number(value[0], f"{name}[0]")
    end = require_finite_number(value[1], f"{name}[1]")
    if end < start:
        raise ValueError(f"{name}[1] must be greater than or equal to {name}[0].")
    return start, end


def _even_sample_interval(time: list[float], *, tolerance: float = _SAMPLE_TOLERANCE) -> tuple[bool, float | None]:
    if len(time) == 1:
        return True, None
    interval = time[1] - time[0]
    if interval <= 0:
        return False, None
    for index in range(2, len(time)):
        current_interval = time[index] - time[index - 1]
        if not math.isclose(current_interval, interval, rel_tol=tolerance, abs_tol=tolerance):
            return False, None
    return True, interval


def slice_signal_window(signal: dict[str, Any], start: float, end: float) -> dict[str, Any]:
    """Return a SignalSeries slice using inclusive original time coordinates."""
    validated, time, values = _validated_time_and_values(signal)
    window = _time_window_pair((start, end), "SignalSeries.window")
    assert window is not None
    window_start, window_end = window

    selected_time: list[float] = []
    selected_values: list[float] = []
    for sample_time, sample_value in zip(time, values, strict=True):
        if window_start <= sample_time <= window_end:
            selected_time.append(sample_time)
            selected_values.append(sample_value)

    if not selected_time:
        raise ValueError("No SignalSeries samples are inside the requested time window.")

    return validate_signal_series(
        {
            "kind": validated["kind"],
            "version": validated["version"],
            "signalId": validated["signalId"],
            "label": validated["label"],
            "quantity": validated["quantity"],
            "unit": validated["unit"],
            "timeUnit": validated["timeUnit"],
            "time": selected_time,
            "values": selected_values,
        }
    )


def summarize_signal_channel(
    signal: dict[str, Any],
    *,
    time_window: Sequence[float] | None = None,
) -> dict[str, Any]:
    window = _time_window_pair(time_window, "SignalSeries.time_window")
    selected_signal = slice_signal_window(signal, window[0], window[1]) if window is not None else validate_signal_series(signal)
    validated, time, values = _validated_time_and_values(selected_signal)
    evenly_sampled, sample_interval = _even_sample_interval(time)

    summary: dict[str, Any] = {
        "kind": "openplazma.signal_channel_summary",
        "version": "0.1.0",
        "signalId": validated["signalId"],
        "label": validated["label"],
        "quantity": validated["quantity"],
        "unit": validated["unit"],
        "timeUnit": validated["timeUnit"],
        "pointCount": len(values),
        "timeRange": [time[0], time[-1]],
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "sampleIntervalSec": sample_interval,
        "evenlySampled": evenly_sampled,
    }
    if window is not None:
        summary["requestedTimeWindow"] = [window[0], window[1]]
    return summary


def build_signal_channel_index(
    signals: Sequence[dict[str, Any]],
    *,
    time_windows: Sequence[Sequence[float]] | None = None,
) -> dict[str, Any]:
    if len(signals) == 0:
        raise ValueError("Signal channel index requires at least one SignalSeries.")

    channels: list[dict[str, Any]] = []
    channels_by_id: dict[str, dict[str, Any]] = {}
    for signal in signals:
        summary = summarize_signal_channel(signal)
        signal_id = summary["signalId"]
        if signal_id in channels_by_id:
            raise ValueError(f"Duplicate SignalSeries signalId '{signal_id}'.")
        channels.append(summary)
        channels_by_id[signal_id] = summary

    windows: list[dict[str, Any]] = []
    for index, time_window in enumerate(time_windows or []):
        window = _time_window_pair(time_window, f"SignalIndex.timeWindows[{index}]")
        assert window is not None
        window_channels: list[dict[str, Any]] = []
        window_channels_by_id: dict[str, dict[str, Any]] = {}
        for signal in signals:
            try:
                summary = summarize_signal_channel(signal, time_window=window)
            except ValueError as error:
                if "No SignalSeries samples" not in str(error):
                    raise
                continue
            window_channels.append(summary)
            window_channels_by_id[summary["signalId"]] = summary
        windows.append(
            {
                "timeRange": [window[0], window[1]],
                "channelCount": len(window_channels),
                "channels": window_channels,
                "channelsById": window_channels_by_id,
            }
        )

    return {
        "kind": "openplazma.signal_channel_index",
        "version": "0.1.0",
        "channelCount": len(channels),
        "timeRange": [
            min(channel["timeRange"][0] for channel in channels),
            max(channel["timeRange"][1] for channel in channels),
        ],
        "channels": channels,
        "channelsById": channels_by_id,
        "windows": windows,
    }


def compute_signal_spectrum(
    signal: dict[str, Any],
    *,
    time_window: Sequence[float] | None = None,
    spectrum_id: str | None = None,
    max_frequency_hz: float | None = None,
    include_dc: bool = True,
) -> dict[str, Any]:
    window = _time_window_pair(time_window, "SignalSpectrum.time_window")
    selected_signal = slice_signal_window(signal, window[0], window[1]) if window is not None else validate_signal_series(signal)
    validated, time, values = _validated_time_and_values(selected_signal)
    if len(values) < 2:
        raise ValueError("SignalSpectrum requires at least two samples.")

    evenly_sampled, sample_interval = _even_sample_interval(time)
    if not evenly_sampled or sample_interval is None:
        raise ValueError("SignalSpectrum requires an evenly sampled SignalSeries.")

    selected_max_frequency: float | None = None
    if max_frequency_hz is not None:
        selected_max_frequency = require_finite_number(max_frequency_hz, "SignalSpectrum.max_frequency_hz", nonnegative=True)

    point_count = len(values)
    bins: list[dict[str, float | int]] = []
    highest_bin = point_count // 2
    for frequency_bin in range(0, highest_bin + 1):
        frequency_hz = frequency_bin / (point_count * sample_interval)
        if selected_max_frequency is not None and frequency_hz > selected_max_frequency + _SAMPLE_TOLERANCE:
            break
        if frequency_bin == 0 and not include_dc:
            continue

        real = 0.0
        imaginary = 0.0
        for sample_index, sample_value in enumerate(values):
            angle = -2.0 * math.pi * frequency_bin * sample_index / point_count
            real += sample_value * math.cos(angle)
            imaginary += sample_value * math.sin(angle)
        magnitude = math.hypot(real, imaginary)
        amplitude = magnitude / point_count
        if frequency_bin != 0 and not (point_count % 2 == 0 and frequency_bin == highest_bin):
            amplitude *= 2.0
        bins.append(
            {
                "bin": frequency_bin,
                "frequencyHz": frequency_hz,
                "amplitude": amplitude,
                "power": amplitude * amplitude,
                "phaseRad": math.atan2(imaginary, real),
            }
        )

    return {
        "kind": "openplazma.signal_spectrum",
        "version": "0.1.0",
        "spectrumId": spectrum_id or f"spectrum-{validated['signalId']}",
        "sourceSignalId": validated["signalId"],
        "label": f"Spectrum of {validated['label']}",
        "method": "discrete_fourier_transform",
        "frequencyUnit": "Hz",
        "amplitudeUnit": validated["unit"],
        "powerUnit": f"{validated['unit']}^2",
        "sampleIntervalSec": sample_interval,
        "sampleRateHz": 1.0 / sample_interval,
        "pointCount": point_count,
        "timeRange": [time[0], time[-1]],
        "bins": bins,
        "assumptions": ["Input SignalSeries is evenly sampled in seconds."],
        "limitations": ["Basic one-sided DFT artifact; no calibration or instrument model is applied."],
    }
