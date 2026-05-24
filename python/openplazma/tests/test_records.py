import json
from pathlib import Path

import pytest

import openplazma as op


REPO_ROOT = Path(__file__).parents[3]
FIXTURE_RECORD = REPO_ROOT / "data" / "fixtures" / "static" / "sample-001" / "study-record.json"


def test_load_static_study_record():
    record = op.load_study_record(FIXTURE_RECORD)

    assert record["kind"] == "openplazma.study_record"
    assert record["version"] == "0.1.0"
    assert record["shot"]["source"]["provider"] == "STATIC_FIXTURE"
    assert record["observations"]
    assert record["limitations"]


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
