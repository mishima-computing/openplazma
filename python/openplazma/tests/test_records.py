import json
from pathlib import Path

import pytest

import openplazma as op


REPO_ROOT = Path(__file__).parents[3]
FIXTURE_RECORD = REPO_ROOT / "data" / "fixtures" / "static" / "sample-001" / "study-record.json"
REAL_NOAA_RECORD = REPO_ROOT / "data" / "fixtures" / "real" / "noaa-swpc-l1-6h-20260612" / "study-record.json"


def test_load_static_study_record():
    record = op.load_study_record(FIXTURE_RECORD)

    assert record["kind"] == "openplazma.study_record"
    assert record["version"] == "0.1.0"
    assert record["shot"]["source"]["provider"] == "STATIC_FIXTURE"
    assert record["observations"]
    assert record["limitations"]


def test_load_noaa_swpc_real_observation_record():
    record = op.load_study_record(REAL_NOAA_RECORD)

    assert record["source"]["provider"] == "NOAA_SWPC"
    assert record["context"]["safetyClassification"] == "public-web-observation"
    assert record["context"]["target"]["type"] == "public_observation_dataset"
    assert record["shot"]["source"]["kind"] == "measured"
    signal_ids = {signal["signalId"] for signal in record["signals"]}
    assert "solar-wind-proton-density" in signal_ids
    assert "goes-xray-long-flux" in signal_ids
    assert all(len(signal["time"]) == len(signal["values"]) for signal in record["signals"])


def test_noaa_swpc_source_requires_snapshot_provenance():
    record = op.load_study_record(REAL_NOAA_RECORD)
    del record["source"]["sha256"]
    del record["context"]["source"]["sha256"]
    del record["shot"]["source"]["sha256"]

    with pytest.raises(ValueError, match="sha256"):
        op.validate_study_record(record)


def test_save_notebook_study_record(tmp_path):
    output = tmp_path / "study-record.json"
    record = {
        "kind": "openplazma.study_record",
        "version": "0.1.0",
        "studyId": "test-study",
        "createdAt": "2026-05-23T00:00:00.000Z",
        "source": {
            "provider": "STATIC_FIXTURE",
            "sourceLabel": "STATIC_FIXTURE sample signal",
            "shotId": "sample-001",
        },
        "signalsViewed": [{"signalId": "plasma-current"}],
        "observations": [{"text": "Static fixture signal was loaded."}],
        "limitations": ["STATIC_FIXTURE data only."],
    }

    op.save_study_record(record, output)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["source"]["provider"] == "STATIC_FIXTURE"


def test_missing_required_study_record_field_is_rejected():
    with pytest.raises(ValueError, match="missing required"):
        op.validate_study_record({"version": "0.1.0"})


def test_missing_required_kind_version_is_rejected():
    record = {
        "kind": "openplazma.study_record",
        "studyId": "test-study",
        "createdAt": "2026-05-23T00:00:00.000Z",
        "source": {"provider": "STATIC_FIXTURE", "shotId": "sample-001"},
        "signalsViewed": [{"signalId": "plasma-current"}],
        "observations": [{"text": "Static fixture signal was loaded."}],
        "limitations": ["STATIC_FIXTURE data only."],
    }

    with pytest.raises(ValueError, match="missing required"):
        op.validate_study_record(record)


def test_study_record_timestamps_must_be_iso_datetimes():
    record = op.load_study_record(FIXTURE_RECORD)
    record["createdAt"] = "today"
    record["context"]["createdAt"] = "today"
    record["shot"]["recordedAt"] = "today"

    with pytest.raises(ValueError, match="createdAt"):
        op.validate_study_record(record)


def test_study_record_shot_ref_must_match_shot_metadata():
    record = op.load_study_record(FIXTURE_RECORD)
    record["shotRef"]["shotId"] = "not-the-shot"

    with pytest.raises(ValueError, match="shotRef"):
        op.validate_study_record(record)


def test_study_record_viewed_signals_must_exist_in_payload():
    record = op.load_study_record(FIXTURE_RECORD)
    record["signalsViewed"] = [{"signalId": "not-in-signals"}]

    with pytest.raises(ValueError, match="signalsViewed"):
        op.validate_study_record(record)
