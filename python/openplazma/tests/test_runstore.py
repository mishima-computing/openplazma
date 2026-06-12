from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import hashlib
import json
import os
from pathlib import Path
import time

import pytest

import openplazma as op
import openplazma.runstore as runstore_module


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


def test_log_metric_has_no_fixed_metric_count_cap(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.log_metric("first_metric", 1)
    run.log_metric("second_metric", 2)

    assert not hasattr(runstore_module, "MAX_METRICS_PER_RUN")
    assert [metric["name"] for metric in op.load_metrics(run.run_id, run_store=run_store)] == [
        "first_metric",
        "second_metric",
    ]


def test_log_metric_accepts_nested_json_values(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )

    metric = run.log_metric("nested_summary", {"window": [0.0, 1.0], "ok": True, "note": None})

    assert metric["value"] == {"window": [0.0, 1.0], "ok": True, "note": None}


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


def test_log_artifact_records_source_file_byte_size_without_fixed_cap(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    source_path = tmp_path / "large-source.json"
    source_path.write_text("123456789", encoding="utf-8")
    run_dir = run_store / "runs" / run.run_id

    artifact = run.log_artifact("large_artifact", "note", source_path)

    assert not hasattr(runstore_module, "MAX_ARTIFACT_BYTES")
    assert (run_dir / "artifacts" / "large-artifact.json").is_file()
    assert artifact["byteSize"] == source_path.stat().st_size
    assert op.load_manifest(run.run_id, run_store=run_store)["artifacts"] == [artifact]
    assert op.load_run(run.run_id, run_store=run_store)["artifactCount"] == 1


def test_log_artifact_records_json_byte_size_without_fixed_cap(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id

    artifact = run.log_artifact("large_json", "note", {"payload": "x" * 128})
    artifact_path = run_dir / artifact["path"]

    assert artifact_path.is_file()
    assert artifact["byteSize"] == artifact_path.stat().st_size
    assert op.load_manifest(run.run_id, run_store=run_store)["artifacts"] == [artifact]
    assert op.load_run(run.run_id, run_store=run_store)["artifactCount"] == 1


def test_log_content_addressed_source_file_writes_pointer_and_blob(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    source_path = tmp_path / "large-signal.bin"
    source_path.write_bytes(b"0123456789" * 128)

    artifact = run.log_artifact(
        "large_signal",
        "signal_blob",
        source_path,
        content_addressed=True,
        media_type="application/octet-stream",
    )

    blob_ref = artifact["blobRef"]
    blob_path = run_store / blob_ref["path"]
    pointer_path = run_store / "runs" / run.run_id / artifact["path"]
    assert blob_path.is_file()
    assert pointer_path.is_file()
    assert blob_path.read_bytes() == source_path.read_bytes()
    assert blob_ref["digest"] == hashlib.sha256(source_path.read_bytes()).hexdigest()
    assert blob_ref["byteSize"] == source_path.stat().st_size
    assert blob_ref["mediaType"] == "application/octet-stream"
    assert artifact["sha256"] == hashlib.sha256(pointer_path.read_bytes()).hexdigest()
    assert op.load_artifact_blob(artifact, run_store=run_store) == blob_path
    assert op.load_manifest(run.run_id, run_store=run_store)["artifacts"] == [artifact]


def test_log_content_addressed_json_artifact_deduplicates_blob(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    payload = {"kind": "large_summary", "values": list(range(32))}

    first = run.log_artifact("large_json_a", "summary_blob", payload, content_addressed=True)
    second = run.log_artifact("large_json_b", "summary_blob", payload, content_addressed=True)

    assert first["blobRef"]["digest"] == second["blobRef"]["digest"]
    assert first["blobRef"]["path"] == second["blobRef"]["path"]
    assert first["blobRef"]["mediaType"] == "application/json"
    assert len(list((run_store / "blobs" / "sha256").rglob(first["blobRef"]["digest"]))) == 1
    assert op.load_artifact_blob(first, run_store=run_store) == op.load_artifact_blob(second, run_store=run_store)
    assert op.load_run(run.run_id, run_store=run_store)["artifactCount"] == 2


def test_load_manifest_rejects_content_addressed_blob_digest_mismatch(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    source_path = tmp_path / "large-signal.bin"
    source_path.write_bytes(b"signal-bytes")
    artifact = run.log_artifact("large_signal", "signal_blob", source_path, content_addressed=True)
    blob_path = run_store / artifact["blobRef"]["path"]
    blob_path.write_bytes(b"x" * artifact["blobRef"]["byteSize"])

    with pytest.raises(ValueError, match="ArtifactBlobRef.digest"):
        op.load_manifest(run.run_id, run_store=run_store)


def test_log_artifact_accepts_nested_json_metadata(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )

    artifact = run.log_artifact(
        "metadata_summary",
        "note",
        {"ok": True},
        metadata={"window": [0.0, 1.0], "reviewed": True, "note": None},
    )

    assert artifact["metadata"] == {"window": [0.0, 1.0], "reviewed": True, "note": None}


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


def test_start_run_records_multi_machine_partition_identity(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="scale-out",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
        run_group_id="will-o-wisp-campaign",
        machine_id="node-a",
        partition_id="shot-001-window-000",
    )

    assert "-node-a-" in run.run_id
    assert len(run.run_id.rsplit("-", 1)[1]) == 12
    record = op.load_run(run.run_id, run_store=run_store)
    assert record["storeId"].startswith("OPS-")
    assert record["machineId"] == "node-a"
    assert record["runGroupId"] == "will-o-wisp-campaign"
    assert record["partitionId"] == "shot-001-window-000"
    metadata = json.loads((run_store / "runstore.json").read_text(encoding="utf-8"))
    assert metadata["storeId"] == record["storeId"]
    assert metadata["backendKind"] == "local_filesystem"
    assert [event["machineId"] for event in op.iter_events(run.run_id, run_store=run_store)] == ["node-a"]


def test_list_runs_page_and_run_group_summary(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run_ids = []
    for index, machine_id in enumerate(["node-a", "node-b", "node-c"]):
        run = op.start_run(
            project="openplazma-demo",
            campaign="scale-out",
            run_type="notebook_analysis",
            context=sample_context(),
            run_store=run_store,
            run_group_id="will-o-wisp-campaign",
            machine_id=machine_id,
            partition_id=f"partition-{index:03d}",
        )
        run.log_metric("partition_index", index)
        run_ids.append(run.run_id)

    first_page = op.list_runs_page(run_store=run_store, page_size=2)
    assert [record["runId"] for record in first_page["runs"]] == sorted(run_ids)[:2]
    assert first_page["nextCursor"] == sorted(run_ids)[1]
    second_page = op.list_runs_page(run_store=run_store, page_size=2, cursor=first_page["nextCursor"])
    assert [record["runId"] for record in second_page["runs"]] == sorted(run_ids)[2:]
    assert second_page["nextCursor"] is None

    group_records = op.list_run_group("will-o-wisp-campaign", run_store=run_store)
    assert [record["runId"] for record in group_records] == sorted(run_ids)
    summary = op.summarize_run_group("will-o-wisp-campaign", run_store=run_store)
    assert summary["runCount"] == 3
    assert summary["metricCount"] == 3
    assert summary["artifactCount"] == 0
    assert summary["statusCounts"] == {"running": 3}
    assert summary["machineIds"] == ["node-a", "node-b", "node-c"]
    assert summary["partitionIds"] == ["partition-000", "partition-001", "partition-002"]


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


def test_run_record_property_rejects_tampered_valid_run_id_boundary(tmp_path: Path):
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
    record["runId"] = "OPR-20990101-999999"
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="RunRecord.runId"):
        run.run_record


def test_run_finish_rejects_tampered_valid_run_id_boundary(tmp_path: Path):
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
    record["runId"] = "OPR-20990101-999999"
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="RunRecord.runId"):
        run.finish()


def test_run_fail_rejects_tampered_valid_run_id_boundary(tmp_path: Path):
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
    record["runId"] = "OPR-20990101-999999"
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="RunRecord.runId"):
        run.fail("tampered")


def test_context_manager_rejects_tampered_valid_run_id_boundary(tmp_path: Path):
    with pytest.raises(ValueError, match="RunRecord.runId"):
        with op.start_run(
            project="openplazma-demo",
            campaign="read-the-signal",
            run_type="notebook_analysis",
            context=sample_context(),
            run_store=run_store_path(tmp_path),
        ) as run:
            run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
            record = json.loads(run_path.read_text(encoding="utf-8"))
            record["runId"] = "OPR-20990101-999999"
            run_path.write_text(json.dumps(record), encoding="utf-8")


@pytest.mark.parametrize("value", [{"x": float("nan")}, [float("inf")]])
def test_log_metric_rejects_nested_non_finite_values(tmp_path: Path, value: object):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )

    with pytest.raises(ValueError, match="MetricRecord.value"):
        run.log_metric("bad_metric", value)


def test_load_metrics_rejects_nested_non_finite_values(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    metric = {
        "kind": "openplazma.metric",
        "version": "0.1.0",
        "runId": run.run_id,
        "name": "bad_metric",
        "value": {"nested": float("nan")},
        "step": None,
        "createdAt": "2026-05-23T00:00:00.000Z",
    }
    metrics_path = run_store_path(tmp_path) / "runs" / run.run_id / "metrics.jsonl"
    metrics_path.write_text(json.dumps(metric) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON constant|MetricRecord.value"):
        op.load_metrics(run.run_id, run_store=run_store_path(tmp_path))


def test_load_metrics_rejects_truncated_jsonl_line(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    metrics_path = run_store_path(tmp_path) / "runs" / run.run_id / "metrics.jsonl"
    metrics_path.write_text('{"kind":"openplazma.metric"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSONL record"):
        op.load_metrics(run.run_id, run_store=run_store_path(tmp_path))


def test_load_metrics_rejects_jsonl_without_terminal_newline(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    metric = {
        "kind": "openplazma.metric",
        "version": "0.1.0",
        "runId": run.run_id,
        "name": "partial_metric",
        "value": 1,
        "step": None,
        "createdAt": op.load_run(run.run_id, run_store=run_store_path(tmp_path))["createdAt"],
    }
    metrics_path = run_store_path(tmp_path) / "runs" / run.run_id / "metrics.jsonl"
    metrics_path.write_text(json.dumps(metric), encoding="utf-8")

    with pytest.raises(ValueError, match="JSONL file must end with a newline"):
        op.load_metrics(run.run_id, run_store=run_store_path(tmp_path))


def test_iter_metrics_streams_records_without_fixed_count_cap(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    metric_template = {
        "kind": "openplazma.metric",
        "version": "0.1.0",
        "runId": run.run_id,
        "name": "metric",
        "value": 1,
        "step": None,
        "createdAt": op.load_run(run.run_id, run_store=run_store)["createdAt"],
    }
    metrics_path = run_store / "runs" / run.run_id / "metrics.jsonl"
    metrics = [{**metric_template, "name": "first_metric"}, {**metric_template, "name": "second_metric"}]
    metrics_path.write_text("\n".join(json.dumps(metric) for metric in metrics) + "\n", encoding="utf-8")

    assert not hasattr(runstore_module, "MAX_METRICS_PER_RUN")
    assert [metric["name"] for metric in op.iter_metrics(run.run_id, run_store=run_store)] == [
        "first_metric",
        "second_metric",
    ]


def test_load_run_rejects_nonstandard_json_constants(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    run_path.write_text(
        run_path.read_text(encoding="utf-8").replace('"artifactCount": 0', '"artifactCount": NaN'),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid JSON constant"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_load_run_rejects_artifact_count_mismatch(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run.log_artifact("signal_series", "signal_series", sample_signal())
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["artifactCount"] = 0
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="artifactCount"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_load_run_rejects_metric_count_mismatch(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run.log_metric("signal_point_count", 128)
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["metricCount"] = 0
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="metricCount"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_load_run_rejects_context_ref_without_matching_artifact(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["contextRef"] = {"artifactName": "missing_context", "artifactType": "experiment_context"}
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="contextRef"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_load_run_rejects_terminal_status_without_finished_at(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["status"] = "finished"
    record["finishedAt"] = None
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="finishedAt"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_load_run_rejects_running_status_with_finished_at(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["status"] = "running"
    record["finishedAt"] = "2026-05-23T00:00:00.000Z"
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="finishedAt"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_load_run_rejects_terminal_status_without_terminal_event(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run.finish()
    events_path = run_store_path(tmp_path) / "runs" / run.run_id / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events_path.write_text("\n".join(json.dumps(event) for event in events[:-1]) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="terminal event"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_load_run_rejects_running_status_with_terminal_event(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    events_path = run_store_path(tmp_path) / "runs" / run.run_id / "events.jsonl"
    started_event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    terminal_event = {
        "kind": "openplazma.event",
        "version": "0.1.0",
        "runId": run.run_id,
        "eventType": "run_finished",
        "createdAt": started_event["createdAt"],
        "message": "Run finished.",
        "metadata": {},
    }
    with events_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(terminal_event) + "\n")

    with pytest.raises(ValueError, match="terminal event"):
        op.load_run(run.run_id, run_store=run_store_path(tmp_path))


def test_start_run_rejects_non_finite_config_values(tmp_path: Path):
    with pytest.raises(ValueError, match="RunConfig"):
        op.start_run(
            project="openplazma-demo",
            campaign="read-the-signal",
            run_type="notebook_analysis",
            context=sample_context(),
            config={"threshold": float("nan")},
            run_store=run_store_path(tmp_path),
        )


def test_log_artifact_rejects_non_finite_json_data_without_file(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    artifact_path = run_store_path(tmp_path) / "runs" / run.run_id / "artifacts" / "bad-artifact.json"

    with pytest.raises(ValueError, match="ArtifactRecord.data"):
        run.log_artifact("bad_artifact", "note", {"value": float("inf")})

    assert not artifact_path.exists()
    assert op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))["artifacts"] == []


def test_log_artifact_rejects_non_finite_metadata_without_file(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    artifact_path = run_store_path(tmp_path) / "runs" / run.run_id / "artifacts" / "bad-artifact.json"

    with pytest.raises(ValueError, match="ArtifactRecord.metadata"):
        run.log_artifact("bad_artifact", "note", {"ok": True}, metadata={"value": float("nan")})

    assert not artifact_path.exists()
    assert op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))["artifacts"] == []


def test_log_metric_rejects_tampered_run_record_without_appending_metric(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["metricCount"] = "bad-count"
    run_path.write_text(json.dumps(record), encoding="utf-8")
    metrics_path = run_store_path(tmp_path) / "runs" / run.run_id / "metrics.jsonl"

    with pytest.raises(ValueError, match="RunRecord.metricCount"):
        run.log_metric("should_not_append", 1)

    assert metrics_path.read_text(encoding="utf-8") == ""


def test_log_artifact_rejects_tampered_run_record_without_writing_artifact(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    run_path = run_store_path(tmp_path) / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["artifactCount"] = "bad-count"
    run_path.write_text(json.dumps(record), encoding="utf-8")
    artifact_path = run_store_path(tmp_path) / "runs" / run.run_id / "artifacts" / "should-not-write.json"

    with pytest.raises(ValueError, match="RunRecord.artifactCount"):
        run.log_artifact("should_not_write", "note", {"ok": True})

    assert not artifact_path.exists()
    assert op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))["artifacts"] == []


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


def test_load_manifest_rejects_duplicate_artifact_ids(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    first = run.log_artifact("signal_series", "signal_series", sample_signal())
    second = run.log_artifact("study_note", "note", {"ok": True})
    manifest_path = run_store_path(tmp_path) / "runs" / run.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][1]["artifactId"] = first["artifactId"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert second["artifactId"] != first["artifactId"]
    with pytest.raises(ValueError, match="duplicate artifact"):
        op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))


def test_load_manifest_rejects_duplicate_artifact_paths(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    first = run.log_artifact("signal_series", "signal_series", sample_signal())
    run.log_artifact("study_note", "note", {"ok": True})
    manifest_path = run_store_path(tmp_path) / "runs" / run.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][1]["path"] = first["path"]
    manifest["artifacts"][1]["sha256"] = first["sha256"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate artifact"):
        op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))


def test_load_manifest_rejects_missing_artifact_file(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    artifact = run.log_artifact("signal_series", "signal_series", sample_signal())
    artifact_path = run_store_path(tmp_path) / "runs" / run.run_id / artifact["path"]
    artifact_path.unlink()

    with pytest.raises(ValueError, match="Artifact file"):
        op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))


def test_load_manifest_rejects_artifact_sha_mismatch(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    artifact = run.log_artifact("signal_series", "signal_series", sample_signal())
    artifact_path = run_store_path(tmp_path) / "runs" / run.run_id / artifact["path"]
    artifact_path.write_bytes(b"x" * artifact["byteSize"])

    with pytest.raises(ValueError, match="sha256"):
        op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))


def test_load_manifest_rejects_artifact_byte_size_mismatch(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    artifact = run.log_artifact("signal_series", "signal_series", sample_signal())
    manifest_path = run_store / "runs" / run.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["byteSize"] = artifact["byteSize"] + 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="byteSize"):
        op.load_manifest(run.run_id, run_store=run_store)


def test_load_manifest_rejects_artifact_symlink_escape(tmp_path: Path):
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store_path(tmp_path),
    )
    artifact = run.log_artifact("signal_series", "signal_series", sample_signal())
    artifact_path = run_store_path(tmp_path) / "runs" / run.run_id / artifact["path"]
    outside_path = tmp_path / "outside.json"
    outside_path.write_text('{"outside":true}\n', encoding="utf-8")
    artifact_path.unlink()
    artifact_path.symlink_to(outside_path)

    with pytest.raises(ValueError, match="Artifact path"):
        op.load_manifest(run.run_id, run_store=run_store_path(tmp_path))


def test_log_metric_rejects_finished_run_without_partial_append(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.finish()
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    metrics_before = (run_dir / "metrics.jsonl").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="running"):
        run.log_metric("after_finish", 1)

    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "metrics.jsonl").read_text(encoding="utf-8") == metrics_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["status"] == "finished"


def test_log_artifact_rejects_finished_run_without_partial_write(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.finish()
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    manifest_before = (run_dir / "manifest.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="running"):
        run.log_artifact("after_finish", "note", {"ok": True})

    assert not (run_dir / "artifacts" / "after-finish.json").exists()
    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "manifest.json").read_text(encoding="utf-8") == manifest_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["status"] == "finished"


def test_fail_rejects_finished_run_without_terminal_event_append(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.finish()
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="finished"):
        run.fail("late failure")

    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["status"] == "finished"


def test_finish_rejects_failed_run_without_terminal_event_append(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.fail("failed")
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="failed"):
        run.finish()

    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["status"] == "failed"


def test_start_run_retries_colliding_run_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    first = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    original_next_run_id = runstore_module._next_run_id
    calls = 0

    def colliding_next_run_id(run_store_arg: str | Path, *, machine_id: str | None = None) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            return first.run_id
        return original_next_run_id(run_store_arg, machine_id=machine_id)

    monkeypatch.setattr(runstore_module, "_next_run_id", colliding_next_run_id)

    second = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )

    assert second.run_id != first.run_id
    assert calls == 2
    assert [record["runId"] for record in op.list_runs(run_store=run_store)] == [first.run_id, second.run_id]


def test_load_run_rejects_run_record_updated_at_before_created_at(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_path = run_store / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["createdAt"] = "2026-05-24T00:00:02.000Z"
    record["updatedAt"] = "2026-05-24T00:00:01.000Z"
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="updatedAt"):
        op.load_run(run.run_id, run_store=run_store)


def test_load_run_rejects_finished_at_before_updated_at(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.finish()
    run_path = run_store / "runs" / run.run_id / "run.json"
    record = json.loads(run_path.read_text(encoding="utf-8"))
    record["createdAt"] = "2026-05-24T00:00:00.000Z"
    record["updatedAt"] = "2026-05-24T00:00:02.000Z"
    record["finishedAt"] = "2026-05-24T00:00:01.000Z"
    run_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="finishedAt"):
        op.load_run(run.run_id, run_store=run_store)


def test_load_manifest_rejects_updated_at_before_created_at(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    manifest_path = run_store / "runs" / run.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["createdAt"] = "2026-05-24T00:00:02.000Z"
    manifest["updatedAt"] = "2026-05-24T00:00:01.000Z"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="RunManifest.updatedAt"):
        op.load_manifest(run.run_id, run_store=run_store)


def test_load_events_rejects_non_monotonic_event_times(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.log_metric("signal_point_count", 128)
    events_path = run_store / "runs" / run.run_id / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events[0]["createdAt"] = "2026-05-24T00:00:02.000Z"
    events[1]["createdAt"] = "2026-05-24T00:00:01.000Z"
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="EventRecord.createdAt"):
        runstore_module.load_events(run.run_id, run_store=run_store)


def test_load_run_rejects_metric_created_before_run_created_at(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.log_metric("signal_point_count", 128)
    metrics_path = run_store / "runs" / run.run_id / "metrics.jsonl"
    metrics = [json.loads(line) for line in metrics_path.read_text(encoding="utf-8").splitlines()]
    metrics[0]["createdAt"] = "2000-01-01T00:00:00.000Z"
    metrics_path.write_text("\n".join(json.dumps(metric) for metric in metrics) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="MetricRecord.createdAt"):
        op.load_run(run.run_id, run_store=run_store)


def test_load_run_rejects_artifact_created_before_run_created_at(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    artifact = run.log_artifact("signal_series", "signal_series", sample_signal())
    manifest_path = run_store / "runs" / run.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["createdAt"] = "2000-01-01T00:00:00.000Z"
    artifact_path = run_store / "runs" / run.run_id / artifact["path"]
    manifest["artifacts"][0]["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="ArtifactRecord.createdAt"):
        op.load_run(run.run_id, run_store=run_store)


def test_load_events_rejects_duplicate_run_started_event(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    events_path = run_store / "runs" / run.run_id / "events.jsonl"
    started_event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    with events_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(started_event) + "\n")

    with pytest.raises(ValueError, match="run_started"):
        runstore_module.load_events(run.run_id, run_store=run_store)


def test_load_run_rejects_metric_without_metric_logged_event(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.log_metric("signal_point_count", 128)
    events_path = run_store / "runs" / run.run_id / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events = [event for event in events if event["eventType"] != "metric_logged"]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="metric_logged"):
        op.load_run(run.run_id, run_store=run_store)


def test_load_run_rejects_artifact_without_artifact_logged_event(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.log_artifact("signal_series", "signal_series", sample_signal())
    events_path = run_store / "runs" / run.run_id / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events = [event for event in events if event["eventType"] != "artifact_logged"]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact_logged"):
        op.load_run(run.run_id, run_store=run_store)


def test_load_manifest_rejects_updated_at_before_artifact_created_at(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.log_artifact("signal_series", "signal_series", sample_signal())
    manifest_path = run_store / "runs" / run.run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["updatedAt"] = manifest["createdAt"]
    manifest["artifacts"][0]["createdAt"] = "2099-01-01T00:00:00.000Z"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="RunManifest.updatedAt"):
        op.load_manifest(run.run_id, run_store=run_store)


def test_load_run_rejects_terminal_event_created_before_finished_at(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run.finish()
    run_dir = run_store / "runs" / run.run_id
    run_path = run_dir / "run.json"
    run_record = json.loads(run_path.read_text(encoding="utf-8"))
    run_record["updatedAt"] = "2099-01-01T00:00:00.000Z"
    run_record["finishedAt"] = "2099-01-01T00:00:00.000Z"
    run_path.write_text(json.dumps(run_record), encoding="utf-8")
    events_path = run_dir / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events[0]["createdAt"] = run_record["createdAt"]
    events[-1]["createdAt"] = run_record["createdAt"]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="RunRecord.finishedAt"):
        op.load_run(run.run_id, run_store=run_store)


def test_log_metric_rolls_back_when_event_append_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    metrics_before = (run_dir / "metrics.jsonl").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")
    original_write_jsonl = runstore_module._write_jsonl

    def fail_metric_event(path: Path, value: dict) -> None:
        if path.name == "events.jsonl" and value.get("eventType") == "metric_logged":
            raise OSError("event append failed")
        original_write_jsonl(path, value)

    monkeypatch.setattr(runstore_module, "_write_jsonl", fail_metric_event)

    with pytest.raises(OSError, match="event append failed"):
        run.log_metric("partial_metric", 1)

    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "metrics.jsonl").read_text(encoding="utf-8") == metrics_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["metricCount"] == 0


def test_log_metric_rolls_back_when_run_record_save_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    metrics_before = (run_dir / "metrics.jsonl").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    def fail_run_record_save(self: runstore_module.Run, record: dict) -> None:
        raise OSError("run save failed")

    monkeypatch.setattr(runstore_module.Run, "_save_run_record", fail_run_record_save)

    with pytest.raises(OSError, match="run save failed"):
        run.log_metric("partial_metric", 1)

    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "metrics.jsonl").read_text(encoding="utf-8") == metrics_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["metricCount"] == 0


def test_log_artifact_rolls_back_when_event_append_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id
    artifact_path = run_dir / "artifacts" / "partial-artifact.json"
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    manifest_before = (run_dir / "manifest.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")
    original_write_jsonl = runstore_module._write_jsonl

    def fail_artifact_event(path: Path, value: dict) -> None:
        if path.name == "events.jsonl" and value.get("eventType") == "artifact_logged":
            raise OSError("event append failed")
        original_write_jsonl(path, value)

    monkeypatch.setattr(runstore_module, "_write_jsonl", fail_artifact_event)

    with pytest.raises(OSError, match="event append failed"):
        run.log_artifact("partial_artifact", "note", {"ok": True})

    assert not artifact_path.exists()
    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "manifest.json").read_text(encoding="utf-8") == manifest_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_manifest(run.run_id, run_store=run_store)["artifacts"] == []


def test_log_artifact_rolls_back_when_manifest_save_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id
    artifact_path = run_dir / "artifacts" / "partial-artifact.json"
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    manifest_before = (run_dir / "manifest.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    def fail_manifest_save(self: runstore_module.Run, manifest: dict) -> None:
        raise OSError("manifest save failed")

    monkeypatch.setattr(runstore_module.Run, "_save_manifest", fail_manifest_save)

    with pytest.raises(OSError, match="manifest save failed"):
        run.log_artifact("partial_artifact", "note", {"ok": True})

    assert not artifact_path.exists()
    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "manifest.json").read_text(encoding="utf-8") == manifest_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_manifest(run.run_id, run_store=run_store)["artifacts"] == []


def test_log_artifact_rolls_back_when_run_record_save_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id
    artifact_path = run_dir / "artifacts" / "partial-artifact.json"
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    manifest_before = (run_dir / "manifest.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")

    def fail_run_record_save(self: runstore_module.Run, record: dict) -> None:
        raise OSError("run save failed")

    monkeypatch.setattr(runstore_module.Run, "_save_run_record", fail_run_record_save)

    with pytest.raises(OSError, match="run save failed"):
        run.log_artifact("partial_artifact", "note", {"ok": True})

    assert not artifact_path.exists()
    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "manifest.json").read_text(encoding="utf-8") == manifest_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_manifest(run.run_id, run_store=run_store)["artifacts"] == []


def test_finish_rolls_back_when_terminal_event_append_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")
    original_write_jsonl = runstore_module._write_jsonl

    def fail_finished_event(path: Path, value: dict) -> None:
        if path.name == "events.jsonl" and value.get("eventType") == "run_finished":
            raise OSError("event append failed")
        original_write_jsonl(path, value)

    monkeypatch.setattr(runstore_module, "_write_jsonl", fail_finished_event)

    with pytest.raises(OSError, match="event append failed"):
        run.finish()

    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["status"] == "running"


def test_fail_rolls_back_when_terminal_event_append_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    run_dir = run_store / "runs" / run.run_id
    run_json_before = (run_dir / "run.json").read_text(encoding="utf-8")
    events_before = (run_dir / "events.jsonl").read_text(encoding="utf-8")
    original_write_jsonl = runstore_module._write_jsonl

    def fail_failed_event(path: Path, value: dict) -> None:
        if path.name == "events.jsonl" and value.get("eventType") == "run_failed":
            raise OSError("event append failed")
        original_write_jsonl(path, value)

    monkeypatch.setattr(runstore_module, "_write_jsonl", fail_failed_event)

    with pytest.raises(OSError, match="event append failed"):
        run.fail("failed")

    assert (run_dir / "run.json").read_text(encoding="utf-8") == run_json_before
    assert (run_dir / "events.jsonl").read_text(encoding="utf-8") == events_before
    assert op.load_run(run.run_id, run_store=run_store)["status"] == "running"


def test_concurrent_start_run_allocates_unique_consistent_runs(tmp_path: Path):
    run_store = run_store_path(tmp_path)

    def start(index: int) -> str:
        return op.start_run(
            project="openplazma-demo",
            campaign=f"concurrent-{index}",
            run_type="notebook_analysis",
            context=sample_context(),
            run_store=run_store,
        ).run_id

    with ThreadPoolExecutor(max_workers=8) as executor:
        run_ids = list(executor.map(start, range(24)))

    assert len(set(run_ids)) == len(run_ids)
    records = op.list_runs(run_store=run_store)
    assert [record["runId"] for record in records] == sorted(run_ids)
    assert all(record["status"] == "running" for record in records)


def test_concurrent_log_metric_writes_remain_consistent(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )

    def log_metric(index: int) -> None:
        run.log_metric(f"metric_{index:02d}", index)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(log_metric, range(24)))

    record = op.load_run(run.run_id, run_store=run_store)
    metrics = op.load_metrics(run.run_id, run_store=run_store)
    events = runstore_module.load_events(run.run_id, run_store=run_store)
    assert record["metricCount"] == 24
    assert sorted(metric["name"] for metric in metrics) == [f"metric_{index:02d}" for index in range(24)]
    assert sum(1 for event in events if event["eventType"] == "metric_logged") == 24


def test_load_run_waits_for_runstore_lock_held_by_another_thread(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    run = op.start_run(
        project="openplazma-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=sample_context(),
        run_store=run_store,
    )
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        with runstore_module._run_store_write_lock(run_store):
            future = executor.submit(op.load_run, run.run_id, run_store=run_store)
            with pytest.raises(FutureTimeoutError):
                future.result(timeout=0.05)

        assert future.result(timeout=5)["runId"] == run.run_id
    finally:
        executor.shutdown(wait=True)


def test_start_run_clears_dead_pid_stale_lock(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    lock_dir = run_store / ".write.lock"
    lock_dir.mkdir(parents=True)
    lock_dir.joinpath("owner").write_text("pid=999999999\n", encoding="utf-8")

    with runstore_module._RunStoreWriteLock(run_store, timeout_seconds=0.1):
        pass

    assert not lock_dir.exists()


def test_lock_keeps_live_pid_until_timeout(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    lock_dir = run_store / ".write.lock"
    lock_dir.mkdir(parents=True)
    lock_dir.joinpath("owner").write_text(f"pid={os.getpid()}\n", encoding="utf-8")

    with pytest.raises(TimeoutError, match="write lock"):
        with runstore_module._RunStoreWriteLock(run_store, timeout_seconds=0.03):
            pass

    assert lock_dir.exists()


def test_lock_keeps_old_live_pid_until_timeout(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    lock_dir = run_store / ".write.lock"
    lock_dir.mkdir(parents=True)
    lock_dir.joinpath("owner").write_text(f"pid={os.getpid()}\n", encoding="utf-8")
    stale_time = time.time() - 3600
    os.utime(lock_dir / "owner", (stale_time, stale_time))
    os.utime(lock_dir, (stale_time, stale_time))

    with pytest.raises(TimeoutError, match="write lock"):
        with runstore_module._RunStoreWriteLock(run_store, timeout_seconds=0.03):
            pass

    assert lock_dir.exists()
    assert lock_dir.joinpath("owner").read_text(encoding="utf-8") == f"pid={os.getpid()}\n"


def test_lock_keeps_remote_host_owner_until_timeout(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    lock_dir = run_store / ".write.lock"
    lock_dir.mkdir(parents=True)
    owner = "host=remote-node\npid=999999999\nlockId=abc\ncreatedAt=2026-05-24T00:00:00.000Z\n"
    lock_dir.joinpath("owner").write_text(owner, encoding="utf-8")
    stale_time = time.time() - 3600
    os.utime(lock_dir / "owner", (stale_time, stale_time))
    os.utime(lock_dir, (stale_time, stale_time))

    with pytest.raises(TimeoutError, match="write lock"):
        with runstore_module._RunStoreWriteLock(run_store, timeout_seconds=0.03):
            pass

    assert lock_dir.exists()
    assert lock_dir.joinpath("owner").read_text(encoding="utf-8") == owner


def test_lock_clears_malformed_stale_owner_after_grace_period(tmp_path: Path):
    run_store = run_store_path(tmp_path)
    lock_dir = run_store / ".write.lock"
    lock_dir.mkdir(parents=True)
    lock_dir.joinpath("owner").write_text("not a pid\n", encoding="utf-8")
    stale_time = time.time() - 3600
    os.utime(lock_dir / "owner", (stale_time, stale_time))
    os.utime(lock_dir, (stale_time, stale_time))

    with runstore_module._RunStoreWriteLock(run_store, timeout_seconds=0.1):
        pass

    assert not lock_dir.exists()
