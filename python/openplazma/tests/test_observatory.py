from __future__ import annotations

import hashlib
import html
import json
import re
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


def artifact_hrefs(page_html: str) -> list[str]:
    return [html.unescape(value) for value in re.findall(r'href="([^"]+)"', page_html) if "/artifacts/" in value]


def rewrite_signal_artifact_path(manifest_path: Path, artifact_path: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        if artifact["name"] == "signal_series":
            artifact["path"] = artifact_path
            break
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def append_metric(run_store: Path, run_id: str, name: str, value: object) -> None:
    metric = {
        "kind": "openplazma.metric",
        "version": "0.1.0",
        "runId": run_id,
        "name": name,
        "value": value,
        "step": None,
        "createdAt": "2026-05-24T00:00:00Z",
    }
    metrics_path = run_store / "runs" / run_id / "metrics.jsonl"
    with metrics_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(metric, sort_keys=True) + "\n")


def add_manifest_artifact(run_store: Path, run_id: str, name: str, artifact_type: str, payload: dict) -> None:
    run_dir = run_store / "runs" / run_id
    artifact_path = run_dir / "artifacts" / f"{name}.json"
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    relative_path = artifact_path.relative_to(run_dir).as_posix()
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifact_count = len(manifest["artifacts"]) + 1
    manifest["artifacts"].append(
        {
            "kind": "openplazma.artifact",
            "version": "0.1.0",
            "artifactId": f"OPA-20260524-{artifact_count:06d}",
            "runId": run_id,
            "name": name,
            "type": artifact_type,
            "path": relative_path,
            "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            "createdAt": "2026-05-24T00:00:00Z",
            "metadata": {},
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def assert_no_external_references(output_dir: Path) -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in output_dir.rglob("*") if path.is_file())
    lowered = combined.lower()
    assert "http://" not in lowered
    assert "https://" not in lowered
    assert "cdn" not in lowered
    assert "script src" not in lowered
    assert "@import" not in lowered


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
    rewrite_signal_artifact_path(manifest_path, "artifacts/../signal-series.json")

    with pytest.raises(ValueError, match="Artifact path"):
        op.export_observatory_html(run_store=run_store)


def test_observatory_artifact_hrefs_resolve_inside_run_artifacts(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_id = create_sample_run(run_store)

    output_dir = op.export_observatory_html(run_store=run_store)
    detail_page = output_dir / "runs" / f"{run_id}.html"
    detail_html = detail_page.read_text(encoding="utf-8")
    hrefs = artifact_hrefs(detail_html)

    assert hrefs
    for href in hrefs:
        assert ".." in Path(href).parts
        assert not href.startswith("/")
        assert not href.startswith("file://")
        assert not href.startswith("http://")
        assert not href.startswith("https://")
        assert not href.startswith("javascript:")
        assert not href.startswith("data:")

        resolved = (detail_page.parent / href).resolve()
        expected_artifacts_dir = (run_store / "runs" / run_id / "artifacts").resolve()
        run_store_root = run_store.resolve()
        assert expected_artifacts_dir == resolved.parent
        assert run_store_root in resolved.parents
        assert resolved.is_file()


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "../outside.json",
        "artifacts/../outside.json",
        "/artifacts/signal-series.json",
        "file://artifacts/signal-series.json",
        "http://example.invalid/signal-series.json",
        "https://example.invalid/signal-series.json",
        "javascript:alert(1)",
        "data:application/json,{}",
        "artifacts/http://example.invalid/signal-series.json",
        "artifacts/data:application/json",
        "artifacts\\signal-series.json",
    ],
)
def test_observatory_rejects_unsafe_artifact_link_paths(tmp_path: Path, unsafe_path: str):
    run_store = tmp_path / ".openplazma"
    run_id = create_sample_run(run_store)
    manifest_path = run_store / "runs" / run_id / "manifest.json"
    rewrite_signal_artifact_path(manifest_path, unsafe_path)

    with pytest.raises(ValueError, match="Artifact path"):
        op.export_observatory_html(run_store=run_store)


def test_compare_runs_summarizes_metrics_artifacts_source_target_capabilities_and_limitations(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_a = create_sample_run(run_store, project="compare-a")
    run_b = create_sample_run(run_store, project="compare-b")
    append_metric(run_store, run_a, "only_a_metric", 1)
    append_metric(run_store, run_b, "signal_max", 42.0)
    append_metric(run_store, run_a, "operator_note", "alpha")
    append_metric(run_store, run_b, "operator_note", "beta")
    append_metric(run_store, run_a, "boolean_metric", True)
    append_metric(run_store, run_b, "boolean_metric", False)
    add_manifest_artifact(run_store, run_a, "only_a_artifact", "note", {"side": "a"})
    add_manifest_artifact(run_store, run_b, "only_b_artifact", "note", {"side": "b"})

    comparison = op.compare_runs(run_a, run_b, run_store=run_store)

    metrics = {row["name"]: row for row in comparison["metrics"]}
    assert metrics["signal_point_count"]["status"] == "same"
    assert metrics["signal_max"]["status"] == "different"
    assert metrics["signal_max"]["delta"] is not None
    assert metrics["only_a_metric"]["status"] == "only_in_a"
    assert metrics["operator_note"]["status"] == "non_numeric"
    assert metrics["boolean_metric"]["status"] == "non_numeric"
    assert metrics["boolean_metric"]["delta"] is None

    artifacts = {row["key"]: row for row in comparison["artifacts"]}
    assert artifacts["signal_series::signal_series"]["status"] == "same_hash"
    assert artifacts["study_record::study_record"]["status"] == "different_hash"
    assert artifacts["only_a_artifact::note"]["status"] == "only_in_a"
    assert artifacts["only_b_artifact::note"]["status"] == "only_in_b"

    capabilities = {row["field"]: row for row in comparison["capabilities"]}
    assert capabilities["capabilities.controlFacility"]["runAValue"] is False
    assert capabilities["capabilities.controlFacility"]["runBValue"] is False
    assert capabilities["capabilities.controlFacility"]["safetyStatus"] == "safe"
    assert comparison["sourceTarget"][0]["field"] == "source.provider"
    assert comparison["sourceTarget"][0]["runAValue"] == "STATIC_FIXTURE"
    source_target = {row["field"]: row for row in comparison["sourceTarget"]}
    assert source_target["target.label"]["runAValue"] == "Local OpenPlazma RunStore"
    assert comparison["limitations"]["status"] == "same"


def test_export_observatory_compare_html_creates_static_page_and_is_read_only(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_a = create_sample_run(run_store, project="<script>alert(1)</script>")
    run_b = create_sample_run(run_store)

    before_hashes = hash_run_files(run_store)
    compare_path = op.export_observatory_compare_html(run_a, run_b, run_store=run_store)
    after_hashes = hash_run_files(run_store)

    output_dir = run_store / "observatory"
    assert before_hashes == after_hashes
    assert compare_path == output_dir / "compare" / f"{run_a}__vs__{run_b}.html"
    assert compare_path.is_file()
    assert (output_dir / "index.html").is_file()
    assert (output_dir / "runs" / f"{run_a}.html").is_file()
    assert (output_dir / "runs" / f"{run_b}.html").is_file()

    compare_html = compare_path.read_text(encoding="utf-8")
    assert run_a in compare_html
    assert run_b in compare_html
    assert "Metric Comparison" in compare_html
    assert "Artifact Comparison" in compare_html
    assert "Capability Comparison" in compare_html
    assert "Limitations Comparison" in compare_html
    assert "STATIC_FIXTURE" in compare_html
    assert "controlFacility" in compare_html
    assert "<script>alert(1)</script>" not in compare_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in compare_html
    assert_no_external_references(output_dir)


def test_compare_artifact_hrefs_resolve_inside_run_artifacts(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_a = create_sample_run(run_store)
    run_b = create_sample_run(run_store)

    compare_path = op.export_observatory_compare_html(run_a, run_b, run_store=run_store)
    hrefs = artifact_hrefs(compare_path.read_text(encoding="utf-8"))

    assert hrefs
    for href in hrefs:
        assert ".." in Path(href).parts
        assert not href.startswith("/")
        assert not href.startswith("file://")
        assert not href.startswith("http://")
        assert not href.startswith("https://")
        assert not href.startswith("javascript:")
        assert not href.startswith("data:")

        match = re.search(r"\.\./\.\./runs/(OPR-\d{8}-\d{6})/artifacts/", href)
        assert match is not None
        href_run_id = match.group(1)
        resolved = (compare_path.parent / href).resolve()
        expected_artifacts_dir = (run_store / "runs" / href_run_id / "artifacts").resolve()
        run_store_root = run_store.resolve()
        assert expected_artifacts_dir == resolved.parent
        assert run_store_root in resolved.parents
        assert resolved.is_file()


def test_compare_rejects_invalid_missing_or_identical_runs(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_id = create_sample_run(run_store)

    with pytest.raises(ValueError, match="distinct"):
        op.compare_runs(run_id, run_id, run_store=run_store)
    with pytest.raises(ValueError, match="run_id"):
        op.compare_runs("../bad", run_id, run_store=run_store)
    with pytest.raises(FileNotFoundError, match="was not found"):
        op.compare_runs("OPR-20990101-999999", run_id, run_store=run_store)


def test_compare_page_flags_unsafe_capability_without_normalizing(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    run_a = create_sample_run(run_store)
    run_b = create_sample_run(run_store)
    run_b_path = run_store / "runs" / run_b / "run.json"
    run_b_record = json.loads(run_b_path.read_text(encoding="utf-8"))
    run_b_record["capabilities"]["controlFacility"] = True
    run_b_path.write_text(json.dumps(run_b_record, indent=2) + "\n", encoding="utf-8")

    comparison = op.compare_runs(run_a, run_b, run_store=run_store)
    capabilities = {row["field"]: row for row in comparison["capabilities"]}
    compare_path = op.export_observatory_compare_html(run_a, run_b, run_store=run_store)
    compare_html = compare_path.read_text(encoding="utf-8")
    detail_html = (run_store / "observatory" / "runs" / f"{run_b}.html").read_text(encoding="utf-8")

    assert capabilities["capabilities.controlFacility"]["runBValue"] is True
    assert capabilities["capabilities.controlFacility"]["safetyStatus"] == "unsafe_true"
    assert "unsafe_true" in compare_html
    assert 'class="unsafe">True' in detail_html
