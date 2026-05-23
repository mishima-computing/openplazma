from pathlib import Path

import pytest

import openplazma as op


REPO_ROOT = Path(__file__).parents[3]


def test_load_matching_static_fixture_signal():
    signal = op.load_static_signal(REPO_ROOT, "sample-001", "plasma-current")

    assert signal["signalId"] == "plasma-current"
    assert signal["unit"] == "kA"
    assert len(signal["time"]) == len(signal["values"])


def test_missing_static_fixture_signal_is_rejected():
    with pytest.raises(ValueError, match="not found"):
        op.load_static_signal(REPO_ROOT, "sample-001", "missing-signal")
