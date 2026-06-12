"""Forward/inverse MHD analysis, mirroring packages/analysis/src/index.ts.

Analytic and read-only: the forward model is a closed-form tearing-mode
signature; the inverse recovers mode numbers and ELM statistics from signals.
No facility control, no live telemetry, no solver.
"""

from __future__ import annotations

import math
from typing import Any

TWO_PI = 2 * math.pi


def unwrap_phase(phases: list[float]) -> list[float]:
    out: list[float] = []
    offset = 0.0
    prev = 0.0
    for index, phase in enumerate(phases):
        if index == 0:
            prev = phase
            out.append(phase)
            continue
        delta = phase + offset - prev
        while delta > math.pi:
            offset -= TWO_PI
            delta -= TWO_PI
        while delta < -math.pi:
            offset += TWO_PI
            delta += TWO_PI
        value = phase + offset
        out.append(value)
        prev = value
    return out


def goertzel_phase_amplitude(values: list[float], dt: float, freq_hz: float) -> tuple[float, float]:
    """Single-frequency DFT bin. Returns (amplitude, phase) for A*cos(wt+phi)."""
    n = len(values)
    if n == 0 or dt <= 0:
        return (0.0, 0.0)
    cos_sum = 0.0
    sin_sum = 0.0
    for i, v in enumerate(values):
        angle = TWO_PI * freq_hz * (i * dt)
        cos_sum += v * math.cos(angle)
        sin_sum += v * math.sin(angle)
    amplitude = (2 / n) * math.hypot(cos_sum, sin_sum)
    phase = math.atan2(-sin_sum, cos_sum)
    return (amplitude, phase)


def linear_fit(x: list[float], y: list[float]) -> tuple[float, float, float]:
    """Returns (slope, intercept, r2)."""
    n = min(len(x), len(y))
    if n < 2:
        return (0.0, y[0] if y else 0.0, 0.0)
    mx = sum(x[:n]) / n
    my = sum(y[:n]) / n
    sxx = sxy = syy = 0.0
    for i in range(n):
        dx = x[i] - mx
        dy = y[i] - my
        sxx += dx * dx
        sxy += dx * dy
        syy += dy * dy
    slope = 0.0 if sxx == 0 else sxy / sxx
    intercept = my - slope * mx
    r2 = 0.0 if sxx == 0 or syy == 0 else (sxy * sxy) / (sxx * syy)
    return (slope, intercept, r2)


def forward_tearing_mode_signal(
    poloidal_angle: float,
    toroidal_angle: float,
    m: int,
    n: int,
    amplitude: float,
    rotation_freq_hz: float,
    phase_rad: float,
    time: list[float],
) -> list[float]:
    """b ~ A*cos(m*theta - n*phi - 2*pi*f*t + phase0) for one probe."""
    spatial = m * poloidal_angle - n * toroidal_angle + phase_rad
    return [amplitude * math.cos(spatial - TWO_PI * rotation_freq_hz * t) for t in time]


def _infer_dt(time: list[float]) -> float:
    if len(time) < 2:
        return 0.0
    return (time[-1] - time[0]) / (len(time) - 1)


def estimate_toroidal_mode_number(
    angles: list[float],
    signals: list[list[float]],
    dt: float,
    freq_hz: float,
) -> dict[str, Any]:
    """Phase-fit the toroidal mode number n across a probe array.

    angles[k] is the toroidal angle of probe k; signals[k] its samples.
    """
    samples = []
    for angle, values in zip(angles, signals):
        _, phase = goertzel_phase_amplitude(values, dt, freq_hz)
        samples.append((angle, phase))
    samples.sort(key=lambda pair: pair[0])
    xs = [pair[0] for pair in samples]
    phases = unwrap_phase([pair[1] for pair in samples])
    slope, _, r2 = linear_fit(xs, phases)
    return {
        "toroidalModeNumber": round(slope),
        "confidence": max(0.0, min(1.0, r2)),
        "method": "phase_fit_toroidal",
    }


def dominant_frequency(values: list[float], dt: float, max_freq_hz: float | None = None) -> float:
    """Coarse grid scan + golden-ish refinement for the dominant component."""
    n = len(values)
    if n < 4 or dt <= 0:
        return 0.0
    nyquist = 1 / (2 * dt)
    top = min(max_freq_hz, nyquist) if max_freq_hz is not None else nyquist
    min_freq = 1 / (n * dt)
    steps = 256
    best_freq = min_freq
    best_amp = -1.0
    for s in range(steps + 1):
        freq = min_freq + (top - min_freq) * s / steps
        amp, _ = goertzel_phase_amplitude(values, dt, freq)
        if amp > best_amp:
            best_amp = amp
            best_freq = freq
    span = (top - min_freq) / steps
    lo = max(min_freq, best_freq - span)
    hi = min(top, best_freq + span)
    for _ in range(20):
        mid1 = lo + (hi - lo) / 3
        mid2 = hi - (hi - lo) / 3
        a1, _ = goertzel_phase_amplitude(values, dt, mid1)
        a2, _ = goertzel_phase_amplitude(values, dt, mid2)
        if a1 >= a2:
            hi = mid2
        else:
            lo = mid1
    return (lo + hi) / 2


def _window_slice(time: list[float], values: list[float], window: tuple[float, float]) -> list[float]:
    out = []
    for t, v in zip(time, values):
        if window[0] <= t <= window[1]:
            out.append(v)
    return out or values


def track_rotation_frequency(
    time: list[float],
    reference_values: list[float],
    window_samples: int | None = None,
    step_samples: int | None = None,
) -> list[dict[str, float]]:
    dt = _infer_dt(time)
    n = len(reference_values)
    win = max(8, window_samples or n // 12)
    step = max(1, step_samples or win // 2)
    track: list[dict[str, float]] = []
    start = 0
    while start + win <= n:
        chunk = reference_values[start : start + win]
        freq = dominant_frequency(chunk, dt)
        amp, _ = goertzel_phase_amplitude(chunk, dt, freq)
        centre = start + win // 2
        track.append({"time": time[centre] if centre < len(time) else 0.0, "rotationFreqHz": freq, "amplitude": amp})
        start += step
    return track


def detect_mode_locking(
    track: list[dict[str, float]],
    lock_freq_threshold_hz: float | None = None,
    min_amplitude_fraction: float = 0.3,
) -> dict[str, Any]:
    if not track:
        return {"locked": False, "lockTimeRange": None}
    peak_amp = max(p["amplitude"] for p in track)
    amp_floor = peak_amp * min_amplitude_fraction
    max_freq = max(p["rotationFreqHz"] for p in track)
    threshold = lock_freq_threshold_hz if lock_freq_threshold_hz is not None else max(50.0, max_freq * 0.1)
    lock_start = None
    lock_end = None
    for p in track:
        if p["rotationFreqHz"] <= threshold and p["amplitude"] >= amp_floor:
            if lock_start is None:
                lock_start = p["time"]
            lock_end = p["time"]
    if lock_start is None or lock_end is None:
        return {"locked": False, "lockTimeRange": None}
    return {"locked": True, "lockTimeRange": [lock_start, lock_end]}


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def detect_periodic_crashes(
    values: list[float],
    time: list[float],
    threshold_sigma: float = 2.0,
    min_spacing_sec: float = 0.0,
) -> list[dict[str, float]]:
    """Sharp local maxima above an adaptive threshold (ELM or sawtooth crashes)."""
    n = len(values)
    if n < 3:
        return []
    threshold = _mean(values) + threshold_sigma * _stddev(values)
    dt = _infer_dt(time)
    crashes: list[dict[str, float]] = []
    last_time = float("-inf")
    for i in range(1, n - 1):
        v = values[i]
        if v > threshold and v >= values[i - 1] and v > values[i + 1]:
            t = time[i] if i < len(time) else i * dt
            if t - last_time >= min_spacing_sec:
                crashes.append({"time": t, "amplitude": v})
                last_time = t
    return crashes


def detect_elm_crashes(
    values: list[float],
    time: list[float],
    threshold_sigma: float = 2.0,
    min_spacing_sec: float = 0.0,
) -> list[dict[str, float]]:
    """Alias of :func:`detect_periodic_crashes` for ELM call sites."""
    return detect_periodic_crashes(values, time, threshold_sigma, min_spacing_sec)


def detect_threshold_crossing(values: list[float], time: list[float], threshold: float) -> dict[str, Any]:
    """First time the signal rises to or above ``threshold``."""
    for i, v in enumerate(values):
        if v >= threshold:
            return {"crossed": True, "time": time[i] if i < len(time) else None}
    return {"crossed": False, "time": None}


def estimate_ntm_island_width(amplitude: float, gain_m_per_sqrt_au: float = 1.0) -> float:
    """Island width ~ gain * sqrt(amplitude). Educational scaling only."""
    return gain_m_per_sqrt_au * math.sqrt(max(0.0, amplitude))


def build_inference_from_array(
    array: dict[str, Any],
    signals: list[dict[str, Any]],
    island_width_gain: float | None = None,
    mode_window: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Estimate the toroidal mode number, rotation, and locking for an array."""
    by_id = {s["signalId"]: s for s in signals}
    channels = array["channels"]
    ref = next((by_id[c["signalId"]] for c in channels if c["signalId"] in by_id), None)
    if ref is None:
        raise ValueError("build_inference_from_array: no channel signals found.")
    time = [float(t) for t in ref["time"]]
    dt = _infer_dt(time)
    t0, t1 = time[0], time[-1]
    window = mode_window or (t0, t0 + (t1 - t0) * 0.4)

    angles = []
    sliced = []
    for channel in channels:
        signal = by_id.get(channel["signalId"])
        if signal is None:
            continue
        angles.append(float(channel["geometry"]["toroidalAngleRad"]))
        sliced.append(_window_slice([float(t) for t in signal["time"]], [float(v) for v in signal["values"]], window))
    freq = dominant_frequency(sliced[0], dt) if sliced else 0.0
    mode_estimate = estimate_toroidal_mode_number(angles, sliced, dt, freq)

    track = track_rotation_frequency(time, [float(v) for v in ref["values"]])
    locking = detect_mode_locking(track)
    nyquist_n = len(channels) // 2

    if island_width_gain is not None:
        peak_amp = max((p["amplitude"] for p in track), default=0.0)
        mode_estimate["islandWidthM"] = estimate_ntm_island_width(peak_amp, island_width_gain)

    inference_id = f"inf-{array['arrayId']}"
    return {
        "kind": "openplazma.inference",
        "version": "0.1.0",
        "inferenceId": inference_id,
        "label": f"Phase-fit mode estimate for {array['label']}",
        "method": "magnetic_mode_phase_fit",
        "sourceArrayId": array["arrayId"],
        "evidenceReadoutIds": [f"{inference_id}-phase-fit-readout"],
        "modeEstimate": mode_estimate,
        "rotationTrack": track,
        "lockingDetected": locking["locked"],
        "lockTimeRange": locking["lockTimeRange"],
        "assumptions": ["Single dominant rotating mode within the analysis window."],
        "limitations": [
            f"Toroidal mode number resolved only up to |n| <= {nyquist_n} (Nyquist).",
            "Rotation frequency estimated per window.",
        ],
        "alternatives": [
            "Higher toroidal mode numbers can alias onto the principal value.",
            "Multiple simultaneous modes can bias a single-mode phase fit.",
        ],
    }


def _classify_elms(frequency_hz: float, regularity: float) -> str:
    if frequency_hz <= 0:
        return "unknown"
    if regularity >= 0.6:
        return "type_I"
    if frequency_hz > 200:
        return "type_III"
    return "unknown"


def analyze_elms(
    signal: dict[str, Any],
    threshold_sigma: float = 2.0,
    min_spacing_sec: float = 0.0,
    analysis_id: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    values = [float(v) for v in signal["values"]]
    time = [float(t) for t in signal["time"]]
    crashes = detect_elm_crashes(values, time, threshold_sigma, min_spacing_sec)
    intervals = [crashes[i]["time"] - crashes[i - 1]["time"] for i in range(1, len(crashes))]
    mean_interval = _mean(intervals)
    frequency = 1 / mean_interval if mean_interval > 0 else 0.0
    cv = (_stddev(intervals) / mean_interval) if mean_interval > 0 else 1.0
    regularity = 0.0 if not intervals else max(0.0, min(1.0, 1 - cv))
    return {
        "kind": "openplazma.elm_analysis",
        "version": "0.1.0",
        "analysisId": analysis_id or f"elm-{signal['signalId']}",
        "label": label or f"ELM analysis on {signal['label']}",
        "sourceSignalId": signal["signalId"],
        "crashes": crashes,
        "elmFrequencyHz": frequency,
        "regularity": regularity,
        "classification": _classify_elms(frequency, regularity),
        "assumptions": [
            "Crashes appear as sharp positive spikes in the source signal.",
            "Crash spacing reflects the ELM cycle.",
        ],
        "limitations": [
            "Threshold-based detection can miss small crashes or merge close ones.",
            "Classification is a coarse heuristic, not a pedestal-stability calculation.",
        ],
    }
