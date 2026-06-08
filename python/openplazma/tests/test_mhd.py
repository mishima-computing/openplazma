from __future__ import annotations

import math
from pathlib import Path

import pytest

from openplazma import (
    analyze_elms,
    detect_periodic_crashes,
    detect_threshold_crossing,
    estimate_ntm_island_width,
    estimate_toroidal_mode_number,
    forward_tearing_mode_signal,
    import_mirnov_array_csv,
    load_study_record,
    validate_mhd_analysis_bundle,
)

REPO_ROOT = Path(__file__).parents[3]
STATIC = REPO_ROOT / "data" / "fixtures" / "static"
MHD_FIXTURE = STATIC / "mhd-mode-001" / "study-record.json"
ELM_FIXTURE = STATIC / "elm-h-mode-001" / "study-record.json"
SAWTOOTH_FIXTURE = STATIC / "sawtooth-001" / "study-record.json"
NTM_FIXTURE = STATIC / "ntm-3-2-001" / "study-record.json"
DENSITY_FIXTURE = STATIC / "density-limit-001" / "study-record.json"

TWO_PI = 2 * math.pi


def test_mhd_fixture_validates():
    record = load_study_record(MHD_FIXTURE)
    assert record["mhd"]["arrays"][0]["channels"].__len__() == 8
    assert record["mhd"]["observationModels"][0]["modelId"] == "tm-2-1"


def test_elm_fixture_validates():
    record = load_study_record(ELM_FIXTURE)
    elm = record["mhd"]["elmAnalyses"][0]
    assert elm["classification"] == "type_I"
    assert len(elm["crashes"]) == 10


def test_forward_inverse_round_trip_recovers_n():
    channels = 8
    dt = 1e-4
    freq = 2000.0
    time = [i * dt for i in range(2000)]
    angles = [(k * TWO_PI) / channels for k in range(channels)]
    signals = [
        forward_tearing_mode_signal(0.0, angle, 2, 1, 1.0, freq, 0.4, time)
        for angle in angles
    ]
    estimate = estimate_toroidal_mode_number(angles, signals, dt, freq)
    assert estimate["toroidalModeNumber"] == 1
    assert estimate["confidence"] > 0.95


def test_n_aliasing_returns_principal_value():
    channels = 8
    dt = 1e-4
    freq = 2000.0
    time = [i * dt for i in range(2000)]
    angles = [(k * TWO_PI) / channels for k in range(channels)]
    signals = [
        forward_tearing_mode_signal(0.0, angle, 2, 9, 1.0, freq, 0.0, time)
        for angle in angles
    ]
    estimate = estimate_toroidal_mode_number(angles, signals, dt, freq)
    assert estimate["toroidalModeNumber"] == 1


def test_analyze_elms_recovers_frequency_and_type():
    dt = 1e-4
    period = 0.01
    count = 10
    width = dt * 1.5
    samples = int((count + 1) * period / dt)
    time = [i * dt for i in range(samples)]
    crash_times = [(k + 1) * period for k in range(count)]
    values = []
    for t in time:
        v = 0.2
        for tc in crash_times:
            v += 1.5 * math.exp(-((t - tc) ** 2) / (2 * width * width))
        values.append(v)
    signal = {
        "kind": "openplazma.signal_series",
        "version": "0.1.0",
        "signalId": "d-alpha",
        "label": "D-alpha",
        "quantity": "photon_flux",
        "unit": "a.u.",
        "timeUnit": "s",
        "time": time,
        "values": values,
    }
    analysis = analyze_elms(signal, threshold_sigma=1.5, min_spacing_sec=0.005)
    assert abs(analysis["elmFrequencyHz"] - 100) < 10
    assert analysis["classification"] == "type_I"
    assert len(analysis["crashes"]) == 10


def test_phenomenon_fixtures_validate():
    sawtooth = load_study_record(SAWTOOTH_FIXTURE)
    assert all(e["phenomenon"] == "sawtooth_crash" for e in sawtooth["mhd"]["events"])
    assert len(sawtooth["mhd"]["claims"][0]["eventIds"]) == 12

    ntm = load_study_record(NTM_FIXTURE)
    estimate = ntm["mhd"]["inferences"][0]["modeEstimate"]
    assert estimate["toroidalModeNumber"] == 2
    assert estimate["islandWidthM"] > 0
    assert ntm["mhd"]["inferences"][0]["lockingDetected"] is False

    density = load_study_record(DENSITY_FIXTURE)
    phenomena = {e["phenomenon"] for e in density["mhd"]["events"]}
    assert "density_limit" in phenomena
    assert "radiative_collapse" in phenomena


def test_detect_threshold_and_island():
    crossing = detect_threshold_crossing([0.1, 0.5, 0.9], [0.0, 0.1, 0.2], 0.8)
    assert crossing["crossed"] is True
    assert crossing["time"] == pytest.approx(0.2)
    assert estimate_ntm_island_width(4.0, 0.03) == pytest.approx(0.06)


def test_detect_periodic_crashes_counts_sawteeth():
    dt = 1e-4
    period = 0.004
    count = 12
    width = dt * 1.5
    samples = int((count + 1) * period / dt)
    time = [i * dt for i in range(samples)]
    crash_times = [(k + 1) * period for k in range(count)]
    values = []
    for t in time:
        v = 0.2
        for tc in crash_times:
            v += 1.5 * math.exp(-((t - tc) ** 2) / (2 * width * width))
        values.append(v)
    crashes = detect_periodic_crashes(values, time, threshold_sigma=1.5, min_spacing_sec=0.002)
    assert len(crashes) == 12


def test_import_mirnov_array_csv_recovers_mode(tmp_path):
    channels = 8
    dt = 1e-4
    freq = 2000.0
    samples = 2000
    time = [i * dt for i in range(samples)]
    angles = [(k * TWO_PI) / channels for k in range(channels)]
    columns = {
        f"probe{k + 1}": forward_tearing_mode_signal(0.0, angles[k], 2, 1, 1.0, freq, 0.3, time)
        for k in range(channels)
    }
    csv_path = tmp_path / "mirnov.csv"
    headers = ["time", *columns.keys()]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(headers) + "\n")
        for i, t in enumerate(time):
            row = [f"{t:.6f}"] + [f"{columns[c][i]:.6f}" for c in columns]
            handle.write(",".join(row) + "\n")

    probes = [
        {"column": f"probe{k + 1}", "toroidalAngleRad": angles[k]}
        for k in range(channels)
    ]
    result = import_mirnov_array_csv(csv_path, probes=probes, island_width_gain=0.05)

    assert result["inference"]["modeEstimate"]["toroidalModeNumber"] == 1
    assert result["inference"]["modeEstimate"]["islandWidthM"] > 0
    assert result["context"]["source"]["provider"] == "LOCAL_SIGNAL_FILE"
    assert result["context"]["capabilities"]["controlFacility"] is False
    assert len(result["signals"]) == channels
    # the returned bundle is already schema-validated by the importer
    validate_mhd_analysis_bundle(result["mhd"], {s["signalId"] for s in result["signals"]})


def test_bundle_rejects_dangling_claim():
    bundle = {
        "kind": "openplazma.mhd_analysis_bundle",
        "version": "0.1.0",
        "provenanceKind": "synthetic",
        "arrays": [],
        "events": [],
        "observationModels": [],
        "inferences": [],
        "elmAnalyses": [
            {
                "kind": "openplazma.elm_analysis",
                "version": "0.1.0",
                "analysisId": "elm-1",
                "label": "ELM",
                "sourceSignalId": "d-alpha",
                "crashes": [],
                "elmFrequencyHz": 100,
                "regularity": 0.9,
                "classification": "type_I",
                "assumptions": [],
                "limitations": [],
            }
        ],
        "claims": [
            {
                "kind": "openplazma.claim",
                "version": "0.1.0",
                "claimId": "c1",
                "statement": "bad",
                "elmAnalysisId": "does-not-exist",
                "evidence": [],
            }
        ],
    }
    with pytest.raises(ValueError):
        validate_mhd_analysis_bundle(bundle)
