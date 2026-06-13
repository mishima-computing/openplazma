from __future__ import annotations

import hashlib
import json
from pathlib import Path

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[3]
SHOT_ID = "noaa-swpc-l1-6h-20260612"
SELECTED_SIGNALS = [
    "solar-wind-proton-density",
    "imf-bz-gsm",
    "goes-xray-long-flux",
]


def _runstore_hashes(run_store: Path) -> dict[str, str]:
    return {
        str(path.relative_to(run_store)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(run_store.rglob("*"))
        if path.is_file()
    }


def _artifact_payload(run_store: Path, run_id: str, artifact: dict) -> dict:
    path = run_store / "runs" / run_id / artifact["path"]
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_external_or_mutating_ui(output_dir: Path) -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in output_dir.rglob("*") if path.is_file())
    lowered = combined.lower()
    assert "http://" not in lowered
    assert "https://" not in lowered
    assert "<script" not in lowered
    assert "<form" not in lowered
    assert "<button" not in lowered


def test_noaa_public_observation_campaign_runs_snapshot_to_observatory_end_to_end(tmp_path: Path) -> None:
    run_store = tmp_path / ".openplazma"
    output_dir = tmp_path / "observatory"

    result = op.run_public_observation_campaign(
        repo_root=REPO_ROOT,
        shot_id=SHOT_ID,
        signal_ids=SELECTED_SIGNALS,
        run_store=run_store,
        output_dir=output_dir,
    )

    run_id = result["runId"]
    run = op.load_run(run_id, run_store=run_store)
    manifest = op.load_manifest(run_id, run_store=run_store)
    metrics = op.load_metrics(run_id, run_store=run_store)
    artifact_types = [artifact["type"] for artifact in manifest["artifacts"]]

    assert run["source"]["provider"] == "NOAA_SWPC"
    assert run["source"]["uri"] == f"data/fixtures/real/{SHOT_ID}/source-provenance.json"
    assert run["capabilities"]["readFacilityTelemetry"] is False
    assert run["capabilities"]["controlFacility"] is False
    assert run["status"] == "finished"
    assert set(
        [
            "public_observation_snapshot",
            "source_provenance",
            "signal_channel_index",
            "signal_series",
            "signal_spectrum",
            "investigation_package",
            "investigation_session",
            "investigation_assessment",
            "investigation_report",
        ]
    ).issubset(set(artifact_types))
    assert artifact_types.count("signal_series") == len(SELECTED_SIGNALS)
    assert artifact_types.count("signal_spectrum") == len(SELECTED_SIGNALS)
    assert {metric["name"] for metric in metrics} >= {
        "public_signal_count",
        "selected_signal_count",
        "missing_required_observable_count",
        "investigation_report_count",
    }

    package_artifact = next(artifact for artifact in manifest["artifacts"] if artifact["type"] == "investigation_package")
    report_artifact = next(artifact for artifact in manifest["artifacts"] if artifact["type"] == "investigation_report")
    package = _artifact_payload(run_store, run_id, package_artifact)
    report = _artifact_payload(run_store, run_id, report_artifact)

    assert package["fusionAssessment"]["fusionStatus"] == "unsupported"
    assert package["fusionAssessment"]["conditionMode"] == "forward_from_observations"
    assert {artifact["signalIds"][0] for artifact in package["artifacts"]} == set(SELECTED_SIGNALS)
    assert len(package["observations"]) == len(SELECTED_SIGNALS)
    for artifact in package["artifacts"]:
        assert artifact["source"]["sourceKind"] == "public_snapshot"
        assert artifact["instrument"]["calibration"]["status"] == "unknown"
        assert artifact["signalWindows"][0]["sampleCount"] > 0
        assert artifact["frequencyAnalyses"][0]["bands"]
        assert "fusion" in " ".join(artifact["limitations"]).lower()

    assert all("does not support a fusion claim" in claim["statement"] for claim in report["claims"])
    assert any("calibrated fusion-product evidence" in item for item in report["nextObservations"])
    assert Path(result["reportArtifactPath"]).is_file()

    summary = op.summarize_runstore_multirun(run_store=run_store)
    assert summary["runCount"] == 1
    assert any(row["fusionStatus"] == "unsupported" for row in summary["evidenceSpines"])
    assert {row["signalId"] for row in summary["spectralRows"] if row["signalId"]} >= set(SELECTED_SIGNALS)

    before_export_hashes = _runstore_hashes(run_store)
    exported = op.export_observatory_html(run_store=run_store, output_dir=output_dir)
    after_export_hashes = _runstore_hashes(run_store)

    assert exported == output_dir
    assert before_export_hashes == after_export_hashes
    assert (output_dir / "index.html").is_file()
    assert (output_dir / "runs" / f"{run_id}.html").is_file()
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")
    run_html = (output_dir / "runs" / f"{run_id}.html").read_text(encoding="utf-8")
    combined_html = index_html + run_html
    assert "NOAA_SWPC" in combined_html
    assert "solar-wind-proton-density" in combined_html
    assert "goes-xray-long-flux" in combined_html
    assert "unsupported" in combined_html
    assert "calibrated fusion-product evidence" in combined_html
    assert "Investigation Evidence Spine" in combined_html
    _assert_no_external_or_mutating_ui(output_dir)
