from __future__ import annotations

import math
import shutil
from pathlib import Path

import pytest

from openplazma import public_data
from openplazma import signals as signal_api


REPO_ROOT = Path(__file__).resolve().parents[3]
SHOT_ID = "noaa-swpc-l1-6h-20260612"


def test_load_public_observation_snapshot_validates_provenance_and_indexes_signals() -> None:
    snapshot = public_data.load_public_observation_snapshot(REPO_ROOT, SHOT_ID)

    assert snapshot["provider"] == "NOAA_SWPC"
    assert snapshot["shotId"] == SHOT_ID
    assert snapshot["record"]["kind"] == "openplazma.study_record"
    assert snapshot["provenance"]["kind"] == "openplazma.source_provenance"
    assert snapshot["record"]["source"]["sha256"] == snapshot["provenance"]["bundleSha256"]
    assert snapshot["capabilities"]["readFacilityTelemetry"] is False
    assert snapshot["capabilities"]["controlFacility"] is False

    index = signal_api.build_signal_channel_index(snapshot["signals"], time_windows=[(0.0, 600.0)])
    assert index["kind"] == "openplazma.signal_channel_index"
    assert index["channelCount"] == 11
    assert index["timeRange"] == [0.0, 21420.0]

    density = index["channelsById"]["solar-wind-proton-density"]
    assert density["label"] == "Solar Wind Proton Density"
    assert density["unit"] == "cm^-3"
    assert density["pointCount"] == 343
    assert density["timeRange"] == [0.0, 21360.0]
    assert density["sampleIntervalSec"] is None
    assert density["evenlySampled"] is False

    xray = index["channelsById"]["goes-xray-long-flux"]
    assert xray["sampleIntervalSec"] == 60.0
    assert xray["evenlySampled"] is True

    window_density = index["windows"][0]["channelsById"]["solar-wind-proton-density"]
    assert window_density["timeRange"] == [0.0, 600.0]
    assert window_density["pointCount"] == 11
    assert window_density["sampleIntervalSec"] == 60.0


def test_public_observation_snapshot_rejects_tampered_raw_file(tmp_path: Path) -> None:
    fixture_root = tmp_path / "repo" / "data" / "fixtures" / "real"
    shutil.copytree(REPO_ROOT / "data" / "fixtures" / "real", fixture_root)
    raw_file = fixture_root / SHOT_ID / "raw" / "plasma-6-hour.json"
    raw_bytes = raw_file.read_bytes()
    raw_file.write_bytes(bytes([raw_bytes[0] ^ 1]) + raw_bytes[1:])

    with pytest.raises(ValueError, match="sha256"):
        public_data.load_public_observation_snapshot(tmp_path / "repo", SHOT_ID)


def test_slice_signal_window_keeps_original_time_coordinates_and_summarizes_window() -> None:
    signal = public_data.load_public_observation_signal(REPO_ROOT, SHOT_ID, "solar-wind-proton-density")

    sliced = signal_api.slice_signal_window(signal, 0.0, 180.0)
    assert sliced["signalId"] == "solar-wind-proton-density"
    assert sliced["time"] == [0.0, 60.0, 120.0, 180.0]
    assert sliced["values"] == [0.24, 0.2, 0.38, 0.19]

    summary = signal_api.summarize_signal_channel(signal, time_window=(0.0, 180.0))
    assert summary["pointCount"] == 4
    assert summary["timeRange"] == [0.0, 180.0]
    assert summary["min"] == 0.19
    assert summary["max"] == 0.38
    assert summary["mean"] == pytest.approx(0.2525)


def test_fourier_spectrum_artifact_detects_evenly_sampled_frequency() -> None:
    sample_interval = 0.25
    frequency_hz = 0.5
    time = [index * sample_interval for index in range(64)]
    values = [math.sin(2.0 * math.pi * frequency_hz * item) for item in time]
    signal = {
        "kind": "openplazma.signal_series",
        "version": "0.1.0",
        "signalId": "synthetic-sine",
        "label": "Synthetic sine",
        "quantity": "example",
        "unit": "a.u.",
        "timeUnit": "s",
        "time": time,
        "values": values,
    }

    spectrum = signal_api.compute_signal_spectrum(signal)
    dominant = max(spectrum["bins"][1:], key=lambda item: item["amplitude"])

    assert spectrum["kind"] == "openplazma.signal_spectrum"
    assert spectrum["sourceSignalId"] == "synthetic-sine"
    assert spectrum["sampleIntervalSec"] == sample_interval
    assert spectrum["pointCount"] == 64
    assert dominant["frequencyHz"] == pytest.approx(frequency_hz)
    assert dominant["amplitude"] == pytest.approx(1.0)


def test_fourier_spectrum_requires_even_sampling() -> None:
    signal = {
        "kind": "openplazma.signal_series",
        "version": "0.1.0",
        "signalId": "uneven",
        "label": "Uneven",
        "quantity": "example",
        "unit": "a.u.",
        "timeUnit": "s",
        "time": [0.0, 1.0, 2.1],
        "values": [0.0, 1.0, 0.0],
    }

    with pytest.raises(ValueError, match="evenly sampled"):
        signal_api.compute_signal_spectrum(signal)
