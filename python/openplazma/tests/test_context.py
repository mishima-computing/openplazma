from pathlib import Path

import pytest

import openplazma as op


EXAMPLE_CONTEXT = Path(__file__).parents[3] / "notebooks" / "examples" / "sample-experiment-context.json"


def test_load_sample_experiment_context():
    context = op.load_experiment_context(EXAMPLE_CONTEXT)

    assert context["kind"] == "openplazma.experiment_context"
    assert context["version"] == "0.1.0"
    assert context["contextId"] == "ctx-sample-001-plasma-current-notebook"
    assert context["shotRef"]["provider"] == "STATIC_FIXTURE"
    assert context["shotRef"]["shotId"] == "sample-001"
    assert context["target"]["type"] == "static_fixture"
    assert context["capabilities"]["readData"] is True
    assert context["capabilities"]["writeArtifacts"] is True
    assert context["capabilities"]["runSimulation"] is False
    assert context["capabilities"]["submitComputeJob"] is False
    assert context["capabilities"]["readFacilityTelemetry"] is False
    assert context["capabilities"]["controlFacility"] is False
    assert context["signals"][0]["signalId"] == "plasma-current"


def test_missing_required_experiment_context_field_is_rejected():
    with pytest.raises(ValueError, match="missing required"):
        op.validate_experiment_context(
            {
                "kind": "openplazma.experiment_context",
                "version": "0.1.0",
                "createdAt": "2026-05-23T00:00:00.000Z",
                "shotRef": {"provider": "STATIC_FIXTURE", "shotId": "sample-001"},
                "signals": [{"signalId": "plasma-current"}],
            }
        )


def test_facility_control_capability_is_rejected():
    context = op.load_experiment_context(EXAMPLE_CONTEXT)
    context["capabilities"]["controlFacility"] = True

    with pytest.raises(ValueError, match="controlFacility"):
        op.validate_experiment_context(context)
