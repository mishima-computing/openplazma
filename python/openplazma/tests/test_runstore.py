from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[3]


def sample_context() -> dict:
    return op.load_experiment_context(REPO_ROOT / "notebooks" / "examples" / "sample-experiment-context.json")


def sample_signal() -> dict:
    context = sample_context()
    return op.load_static_signal(REPO_ROOT, context["shotRef"]["shotId"], context["signals"][0]["signalId"])


def run_store_path(tmp_path: Path) -> Path:
    return tmp_path / ".openplazma"


def test_start_run_creates_inspectable_files(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        config={"source": "test"},
        run_store=run_store_path(tmp_path),
    )

    run_dir = run_store_path(tmp_path) / "runs" / run.run_id
    assert run_dir.is_dir()
    assert (run_dir / "run.json").is_file()
    assert (run_dir / "config.json").is_file()
    assert (run_dir / "metrics.jsonl").is_file()
    assert (run_dir / "events.jsonl").is_file()
    assert (run_dir / "artifacts").is_dir()
    assert (run_dir / "manifest.json").is_file()

    record = op.load_run(run.run_id, run_store=run_store_path(tmp_path))
    assert record["kind"] == "openplazma.run"
    assert record["version"] == "0.1.0"
    assert record["status"] == "running"
    assert record["target"]["type"] == "local_run_store"
    assert record["source"]["provider"] == "STATIC_FIXTURE"
    assert record["contextRef"] is None
    assert record["capabilities"]["controlFacility"] is False
    assert record["capabilities"]["readFacilityTelemetry"] is False
    assert record["capabilities"]["runSimulation"] is False
    assert record["capabilities"]["submitComputeJob"] is False

    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    assert config == {"source": "test"}


def test_log_metric_writes_metric_record(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )

    metric = run.log_metric("signal_point_count", 128)

    assert metric["kind"] == "openplazma.metric"
    assert metric["value"] == 128
    metrics = op.load_metrics(run.run_id, run_store=run_store_path(tmp_path))
    assert metrics == [metric]
    assert op.load_run(run.run_id, run_store=run_store_path(tmp_path))["metricCount"] == 1


def test_log_artifact_writes_json_and_manifest_entry(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )

    signal = sample_signal()
    context_artifact = run.log_artifact("experiment_context", "experiment_context", sample_context())
    artifact = run.log_artifact("signal_series", "signal_series", signal)

    run_dir = run_store_path(tmp_path) / "runs" / run.run_id
    artifact_path = run_dir / artifact["path"]
    assert artifact_path.is_file()
    assert artifact["path"] == "artifacts/signal-series.json"
    assert artifact["sha256"] == hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    manifest = op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))
    assert manifest["kind"] == "openplazma.run_manifest"
    assert manifest["artifacts"] == [context_artifact, artifact]
    loaded_run = op.load_run(run.run_id, run_store=run_store_path(tmp_path))
    assert loaded_run["artifactCount"] == 2
    assert loaded_run["contextRef"] == {
        "artifactName": "experiment_context",
        "artifactType": "experiment_context",
    }


def test_finish_and_context_manager_update_run_status(tmp_path: Path):
    with op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    ) as run:
        run.log_metric("signal_peak", 0.91)

    record = op.load_run(run.run_id, run_store=run_store_path(tmp_path))
    assert record["status"] == "finished"
    assert record["finishedAt"] is not None
    events_path = run_store_path(tmp_path) / "runs" / run.run_id / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert [event["eventType"] for event in events] == ["run_started", "metric_logged", "run_finished"]


def test_unsafe_capability_override_is_rejected(tmp_path: Path):
    capabilities = dict(sample_context()["capabilities"])
    capabilities["controlFacility"] = True

    with pytest.raises(ValueError, match="controlFacility"):
        op.start_run(
            project="openplazma-demo",
            campaign="read-the-signal",
            run_type="notebook_analysis",
            context=sample_context(),
            capabilities=capabilities,
            run_store=run_store_path(tmp_path),
        )


def test_fair_mast_provider_is_rejected(tmp_path: Path):
    context = sample_context()
    context["source"]["provider"] = "FAIR_MAST"

    with pytest.raises(ValueError, match="STATIC_FIXTURE"):
        op.start_run(
            project="openplazma-demo",
            campaign="read-the-signal",
            run_type="notebook_analysis",
            context=context,
            run_store=run_store_path(tmp_path),
        )


def test_list_runs_and_load_run(tmp_path: Path):
    first = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    second = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )

    runs = op.list_runs(run_store=run_store_path(tmp_path))
    assert [run["runId"] for run in runs] == [first.run_id, second.run_id]
    assert op.load_run(first.run_id, run_store=run_store_path(tmp_path))["runId"] == first.run_id


def test_path_traversal_artifact_name_is_rejected(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )

    with pytest.raises(ValueError, match="ArtifactRecord.name"):
        run.log_artifact("../signal_series", "signal_series", sample_signal())


def test_load_run_rejects_tampered_run_record_boundary(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run_id = run.run_id
    run_path = run_store_path(tmp_path) / "runs" / run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["runId"] = "bad-run-id"
    record["createdAt"] = "today"
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="RunRecord.runId"):
        op.load_run(run_id, run_store=run_store_path(tmp_path))


def test_load_manifest_rejects_tampered_artifact_paths(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run.log_artifact("signal_series", "signal_series", sample_signal())
    manifest_path = run_store_path(tmp_path) / "runs" / run.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["path"] = "https://example.com/leak.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="ArtifactRecord.path"):
        op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))
