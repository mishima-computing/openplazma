from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[3]


def sample_context() -> dict:
    return op.load_experiment_context(REPO_ROOT / "notebooks" / "examples" / "sample-experiment-context.json")


def sample_signal() -> dict:
    context = sample_context()
    return op.load_static_signal(REPO_ROOT, context["shotRef"]["shotId"], context["signals"][0]["signalId"])


def test_create_study_record_from_context():
    context = sample_context()
    record = op.create_study_record(
        context=context,
        observations=[
            {
                "text": "Notebook test observation.",
                "signalId": context["signals"][0]["signalId"],
                "timeRange": context.get("view", {}).get("timeRange"),
            }
        ],
        hypothesis="Notebook-side test hypothesis.",
    )

    assert record["kind"] == "openplazma.study_record"
    assert record["source"]["provider"] == "STATIC_FIXTURE"
    assert record["source"]["inspiredBy"] == "FAIR_MAST"
    assert record["signalsViewed"] == context["signals"]
    assert record["observations"][-1]["text"] == "Notebook test observation."
    assert record["limitations"] == context["limitations"]
    assert any("read-only analysis and decision support" in limitation for limitation in record["limitations"])
    assert any("no command/control path" in limitation for limitation in record["limitations"])


def test_summarize_signal():
    summary = op.summarize_signal(sample_signal())

    assert summary == {
        "point_count": 6,
        "min": 0.0,
        "max": 18.0,
        "mean": 53.0 / 6.0,
    }


def test_log_context_signal_and_study_record_helper(tmp_path: Path):
    context = sample_context()
    signal = sample_signal()
    record = op.create_study_record(context=context, observations=["Helper logged a StudyRecord."])

    with op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=context,
        run_store=tmp_path / ".openplazma",
    ) as run:
        artifacts = op.log_context_signal_and_study_record(run, context, signal, record)

    assert set(artifacts) == {"experiment_context", "signal_series", "study_record"}
    manifest = op.load_manifest(run.run_id, run_store=tmp_path / ".openplazma")
    assert [artifact["name"] for artifact in manifest["artifacts"]] == [
        "experiment_context",
        "signal_series",
        "study_record",
    ]


def test_log_context_signal_and_study_record_rejects_invalid_artifact_data(tmp_path: Path):
    context = sample_context()
    signal = sample_signal()
    record = op.create_study_record(context=context, observations=["Helper logged a StudyRecord."])
    invalid_signal = dict(signal)
    invalid_signal["values"] = []

    with op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=context,
        run_store=tmp_path / ".openplazma",
    ) as run:
        try:
            op.log_context_signal_and_study_record(run, context, invalid_signal, record)
        except ValueError as error:
            assert "SignalSeries" in str(error)
        else:
            raise AssertionError("invalid SignalSeries should be rejected")


def test_local_tracking_example_runs_and_logs_expected_records(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    env = dict(os.environ)
    env["OPENPLAZMA_RUN_STORE"] = str(run_store)
    completed = subprocess.run(
        [sys.executable, "notebooks/examples/local_tracking_notebook.py"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "OpenPlazma RunStore run" in completed.stdout
    runs = op.list_runs(run_store=run_store)
    assert len(runs) == 1
    run_id = runs[0]["runId"]
    run_record = op.load_run(run_id, run_store=run_store)
    assert run_record["status"] == "finished"
    assert run_record["source"]["provider"] == "STATIC_FIXTURE"
    assert run_record["capabilities"]["controlFacility"] is False

    metrics = op.load_metrics(run_id, run_store=run_store)
    assert [metric["name"] for metric in metrics] == [
        "signal_point_count",
        "signal_min",
        "signal_max",
        "signal_mean",
    ]

    run_dir = run_store / "runs" / run_id
    manifest = op.load_manifest(run_id, run_store=run_store)
    artifact_names = [artifact["name"] for artifact in manifest["artifacts"]]
    assert artifact_names == ["experiment_context", "signal_series", "study_record"]
    for artifact in manifest["artifacts"]:
        artifact_path = run_dir / artifact["path"]
        assert artifact_path.resolve().is_relative_to(run_dir.resolve())
        assert artifact["sha256"] == hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events[0]["eventType"] == "run_started"
    assert events[-1]["eventType"] == "run_finished"


def test_local_tracking_example_repeated_runs_get_distinct_ids(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    env = dict(os.environ)
    env["OPENPLAZMA_RUN_STORE"] = str(run_store)
    for _ in range(2):
        subprocess.run(
            [sys.executable, "notebooks/examples/local_runstore_example.py"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

    run_ids = [run["runId"] for run in op.list_runs(run_store=run_store)]
    assert len(run_ids) == 2
    assert len(set(run_ids)) == 2
