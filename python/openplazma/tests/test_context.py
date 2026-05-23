from pathlib import Path

import pytest

import openplazma as op


EXAMPLE_CONTEXT = Path(__file__).parents[3] / "notebooks" / "examples" / "sample-experiment-context.json"


def test_load_sample_experiment_context():
    context = op.load_experiment_context(EXAMPLE_CONTEXT)

    assert context["shotRef"]["provider"] == "STATIC_FIXTURE"
    assert context["shotRef"]["shotId"] == "sample-001"
    assert context["signals"][0]["signalId"] == "plasma-current"


def test_missing_required_experiment_context_field_is_rejected():
    with pytest.raises(ValueError, match="missing required"):
        op.validate_experiment_context(
            {
                "kind": "openplazma.experiment_context",
                "version": "0.1",
                "createdAt": "2026-05-23T00:00:00.000Z",
                "shotRef": {"provider": "STATIC_FIXTURE", "shotId": "sample-001"},
                "signals": [{"signalId": "plasma-current"}],
            }
        )
