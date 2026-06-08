from __future__ import annotations

import math
from pathlib import Path

import pytest

from openplazma import (
    analyze_elms,
    estimate_toroidal_mode_number,
    forward_tearing_mode_signal,
    load_study_record,
    validate_mhd_analysis_bundle,
)

REPO_ROOT = Path(__file__).parents[3]
MHD_FIXTURE = REPO_ROOT / "data" / "fixtures" / "static" / "mhd-mode-001" / "study-record.json"
ELM_FIXTURE = REPO_ROOT / "data" / "fixtures" / "static" / "elm-h-mode-001" / "study-record.json"

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
