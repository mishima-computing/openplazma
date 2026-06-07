from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import openplazma as op


def test_import_local_signal_csv_feeds_runstore_and_study_record(tmp_path: Path) -> None:
    csv_path = tmp_path / "loop_voltage.csv"
    csv_path.write_text("time,value\n0.0,1.0\n0.5,2.5\n1.0,4.0\n", encoding="utf-8")

    imported = op.import_local_signal_csv(
        csv_path,
        signal_id="loop-voltage",
        label="Loop voltage",
        quantity="voltage",
        unit="V",
        shot_id="local-shot-001",
        observations=["Imported a local read-only signal."],
    )
    context = imported["context"]
    signal = imported["signal"]

    assert context["source"]["provider"] == "LOCAL_SIGNAL_FILE"
    assert context["source"]["uri"] == "local-file:loop_voltage.csv"
    assert context["source"]["sha256"] == hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert context["source"]["validationStatus"] == "schema_validated"
    assert context["safetyClassification"] == "read-only-local-signal"
    assert context["capabilities"]["controlFacility"] is False
    assert context["capabilities"]["readFacilityTelemetry"] is False
    assert context["limitations"][0] == "LOCAL_SIGNAL_FILE read-only import."
    assert signal["time"] == [0.0, 0.5, 1.0]
    assert signal["values"] == [1.0, 2.5, 4.0]

    study_record = op.create_study_record(
        context=context,
        observations=[{"text": "Peak value appears at the end of the imported interval."}],
    )
    assert study_record["source"]["provider"] == "LOCAL_SIGNAL_FILE"
    assert study_record["source"]["sha256"] == context["source"]["sha256"]
    assert study_record["limitations"] == context["limitations"]

    with op.start_run(
        project="openplazma-local",
        campaign="local-signal-import",
        run_type="notebook_analysis",
        context=context,
        run_store=tmp_path / ".openplazma",
    ) as run:
        artifacts = op.log_context_signal_and_study_record(run, context, signal, study_record)

    run_record = op.load_run(run.run_id, run_store=tmp_path / ".openplazma")
    assert run_record["source"]["provider"] == "LOCAL_SIGNAL_FILE"
    assert run_record["source"]["sha256"] == context["source"]["sha256"]
    assert run_record["capabilities"]["controlFacility"] is False
    assert set(artifacts) == {"experiment_context", "signal_series", "study_record"}


def test_import_local_signal_csv_rejects_non_finite_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad_signal.csv"
    csv_path.write_text("time,value\n0.0,1.0\n1.0,nan\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-finite"):
        op.import_local_signal_csv(
            csv_path,
            signal_id="bad-signal",
            label="Bad signal",
            quantity="example",
            unit="a.u.",
        )


def test_import_local_signal_csv_rejects_non_monotonic_time(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad_time.csv"
    csv_path.write_text("time,value\n0.0,1.0\n0.0,2.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="strictly increasing"):
        op.import_local_signal_csv(
            csv_path,
            signal_id="bad-time",
            label="Bad time",
            quantity="example",
            unit="a.u.",
        )
