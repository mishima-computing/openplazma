from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[3]


def sample_context() -> dict:
    return op.load_experiment_context(REPO_ROOT / "notebooks" / "examples" / "sample-experiment-context.json")


def sample_signal() -> dict:
    context = sample_context()
    return op.load_static_signal(REPO_ROOT, context["shotRef"]["shotId"], context["signals"][0]["signalId"])


def create_sample_run(run_store: Path, project: str = "openplazma-demo") -> str:
    context = sample_context()
    signal = sample_signal()
    record = op.create_study_record(context=context, observations=["Observatory test observation."])
    summary = op.summarize_signal(signal)
    with op.start_run(
        project=project,
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=context,
        config={"source": "test_observatory.py"},
        run_store=run_store,
    ) as run:
        op.log_context_signal_and_study_record(run, context, signal, record)
        run.log_metric("signal_point_count", summary["point_count"])
        run.log_metric("signal_min", summary["min"])
        run.log_metric("signal_max", summary["max"])
        run.log_metric("signal_mean", summary["mean"])
        return run.run_id


def hash_run_files(run_store: Path) -> dict[str, str]:
    runs_root = run_store / "runs"
    return {
        str(path.relative_to(runs_root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(runs_root.rglob("*"))
        if path.is_file()
    }


def test_summarize_runstore_and_run(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_id = create_sample_run(run_store)

    summaries = op.summarize_runstore(run_store=run_store)
    summary = op.summarize_run(run_id, run_store=run_store)

    assert len(summaries) == 1
    assert summaries[0]["runId"] == run_id
    assert summary["sourceProvider"] == "STATIC_FIXTURE"
    assert summary["targetType"] == "local_run_store"
    assert summary["artifactCount"] == 3
    assert summary["metricCount"] == 4


def test_load_run_artifacts_and_events(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_id = create_sample_run(run_store)

    artifacts = op.load_run_artifacts(run_id, run_store=run_store)
    events = op.load_run_events(run_id, run_store=run_store)

    assert [artifact["name"] for artifact in artifacts] == ["experiment_context", "signal_series", "study_record"]
    assert events[0]["eventType"] == "run_started"
    assert events[-1]["eventType"] == "run_finished"


def test_export_observatory_html_creates_static_report(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    first_run_id = create_sample_run(run_store)
    second_run_id = create_sample_run(run_store)

    before_hashes = hash_run_files(run_store)
    output_dir = op.export_observatory_html(run_store=run_store)
    after_hashes = hash_run_files(run_store)

    assert before_hashes == after_hashes
    assert output_dir == run_store / "observatory"
    assert (output_dir / "index.html").is_file()
    assert (output_dir / "assets" / "observatory.css").is_file()
    assert (output_dir / "runs" / f"{first_run_id}.html").is_file()
    assert (output_dir / "runs" / f"{second_run_id}.html").is_file()

    index_html = (output_dir / "index.html").read_text(encoding="utf-8")
    detail_html = (output_dir / "runs" / f"{first_run_id}.html").read_text(encoding="utf-8")
    assert first_run_id in index_html
    assert second_run_id in index_html
    assert "signal_point_count" in detail_html
    assert "signal_series" in detail_html
    assert "STATIC_FIXTURE" in detail_html
    assert "controlFacility" in detail_html
    assert "http://" not in index_html + detail_html
    assert "https://" not in index_html + detail_html
    assert "script src" not in index_html.lower() + detail_html.lower()


def test_export_observatory_html_escapes_run_values(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_id = create_sample_run(run_store, project="<script>alert(1)</script>")

    output_dir = op.export_observatory_html(run_store=run_store)
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")
    detail_html = (output_dir / "runs" / f"{run_id}.html").read_text(encoding="utf-8")

    assert "<script>alert(1)</script>" not in index_html
    assert "<script>alert(1)</script>" not in detail_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in index_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in detail_html


def test_export_observatory_html_fails_without_runs(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="No RunStore runs"):
        op.export_observatory_html(run_store=tmp_path / ".openplazma")


def test_observatory_rejects_unsafe_run_id_and_artifact_path(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_id = create_sample_run(run_store)

    with pytest.raises(ValueError, match="run_id"):
        op.summarize_run("../bad", run_store=run_store)

    manifest_path = run_store / "runs" / run_id / "manifest.json"
    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(manifest_text.replace("artifacts/signal-series.json", "artifacts/../signal-series.json"), encoding="utf-8")

    with pytest.raises(ValueError, match="Artifact path"):
        op.export_observatory_html(run_store=run_store)
