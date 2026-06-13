from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

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


def _late_campaign() -> tuple[dict, dict]:
    snapshot = op.load_public_observation_snapshot(REPO_ROOT, SHOT_ID)
    campaign = op.build_public_observation_campaign(
        snapshot,
        signal_ids=SELECTED_SIGNALS,
        time_window=[14400.0, 21360.0],
        session_id="session-tamper-late-mixed",
    )
    return snapshot, campaign


def _artifact_records(signal_ids: list[str] | None = None) -> dict[str, dict[str, str]]:
    selected_signal_ids = signal_ids or SELECTED_SIGNALS
    records: dict[str, dict[str, str]] = {}
    counter = 1

    def add(key: str, name: str, artifact_type: str) -> None:
        nonlocal counter
        records[key] = {
            "name": name,
            "type": artifact_type,
            "path": f"artifacts/{name}.json",
            "sha256": f"{counter:064x}",
            "artifactId": f"OPA-20260613-{counter:06d}",
        }
        counter += 1

    add("public_snapshot", "public_snapshot", "public_observation_snapshot")
    add("source_provenance", "source_provenance", "source_provenance")
    add("signal_index", "signal_index", "signal_channel_index")
    for signal_id in selected_signal_ids:
        add(f"signal_series:{signal_id}", f"signal_series_{signal_id}", "signal_series")
        add(f"signal_spectrum:{signal_id}", f"signal_spectrum_{signal_id}", "signal_spectrum")
    add("investigation_package", "investigation_package", "investigation_package")
    add("investigation_report", "investigation_report", "investigation_report")
    return records


def test_public_observation_lineage_audit_ensemble_runs_partitions_to_observatory(tmp_path: Path) -> None:
    run_store = tmp_path / ".openplazma"
    output_dir = tmp_path / "observatory"

    result = op.run_public_observation_lineage_audit_ensemble(
        repo_root=REPO_ROOT,
        shot_id=SHOT_ID,
        signal_ids=SELECTED_SIGNALS,
        run_store=run_store,
        output_dir=output_dir,
    )

    assert result["runGroupSummary"]["runCount"] == 2
    assert result["runGroupSummary"]["partitionIds"] == ["early-even", "late-mixed"]
    assert [partition["partitionId"] for partition in result["partitions"]] == ["early-even", "late-mixed"]

    for partition in result["partitions"]:
        run = op.load_run(partition["runId"], run_store=run_store)
        manifest = op.load_manifest(partition["runId"], run_store=run_store)
        artifact_types = [artifact["type"] for artifact in manifest["artifacts"]]

        assert run["runGroupId"] == result["runGroupId"]
        assert run["partitionId"] == partition["partitionId"]
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
                "observation_lineage_audit",
            ]
        ).issubset(set(artifact_types))
        assert artifact_types.count("signal_series") == len(SELECTED_SIGNALS)
        assert artifact_types.count("signal_spectrum") == len(SELECTED_SIGNALS)

        audit_artifact = next(artifact for artifact in manifest["artifacts"] if artifact["type"] == "observation_lineage_audit")
        audit = _artifact_payload(run_store, partition["runId"], audit_artifact)
        assert audit["kind"] == "openplazma.observation_lineage_audit"
        assert audit["status"] == "passed"
        assert audit["runGroupId"] == result["runGroupId"]
        assert audit["partitionId"] == partition["partitionId"]
        assert audit["fusionAssessment"]["fusionStatus"] == "unsupported"
        assert audit["fusionAssessment"]["positiveFusionInference"] is False
        assert {"neutron_flux", "gamma_ray"}.issubset(set(audit["fusionAssessment"]["missingObservables"]))
        assert audit["calibrationSummary"]["status"] == "unknown"
        assert {claim["admissibility"] for claim in audit["claimAudits"]} == {"admissible"}
        assert all(claim["positiveFusionClaim"] is False for claim in audit["claimAudits"])
        for ref in [*audit["sourceRefs"], *audit["transformRefs"]]:
            for key in ["artifactName", "artifactType", "path", "sha256", "runArtifactId"]:
                assert isinstance(ref[key], str)
                assert ref[key]
            assert ref["path"].startswith("artifacts/")
        assert audit_artifact["metadata"]["auditStatus"] == "passed"
        assert audit_artifact["metadata"]["partitionId"] == partition["partitionId"]
        assert audit_artifact["metadata"]["calibrationStatus"] == "unknown"

        if partition["partitionId"] == "late-mixed":
            assert any(row["status"] == "not_computed" for row in audit["spectrumLineage"])
        else:
            assert {row["status"] for row in audit["spectrumLineage"]} == {"computed"}

    summary = op.summarize_runstore_multirun(run_store=run_store)
    assert summary["runCount"] == 2
    assert len(summary["lineageAudits"]) == 2
    assert {row["partitionId"] for row in summary["lineageAudits"]} == {"early-even", "late-mixed"}
    assert all(row["auditStatus"] == "passed" for row in summary["lineageAudits"])

    before_export_hashes = _runstore_hashes(run_store)
    exported = op.export_observatory_html(run_store=run_store, output_dir=output_dir)
    after_export_hashes = _runstore_hashes(run_store)

    assert exported == output_dir
    assert before_export_hashes == after_export_hashes
    assert (output_dir / "index.html").is_file()
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Lineage Audit" in index_html
    assert "early-even" in index_html
    assert "late-mixed" in index_html
    assert "not_computed" in index_html
    for run_id in result["runIds"]:
        run_html = (output_dir / "runs" / f"{run_id}.html").read_text(encoding="utf-8")
        assert "Lineage Audit" in run_html
        assert "unsupported" in run_html
        assert "unknown" in run_html
    _assert_no_external_or_mutating_ui(output_dir)


def test_observation_lineage_audit_rejects_missing_mediated_readout_evidence() -> None:
    snapshot, campaign = _late_campaign()
    campaign["package"]["claims"][0]["evidenceReadoutIds"] = []
    campaign["report"]["claims"][0]["evidenceReadoutIds"] = []

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )

    assert audit["status"] == "failed"
    assert any("requires mediated readout evidence" in reason for reason in audit["failureReasons"])
    with pytest.raises(ValueError, match="Observation lineage audit failed"):
        op.validate_observation_lineage_audit(audit)


def test_observation_lineage_audit_rejects_public_window_positive_fusion_claim() -> None:
    snapshot, campaign = _late_campaign()
    positive_claim = {
        **campaign["package"]["claims"][0],
        "claimId": "claim-public-window-positive-fusion",
        "statement": "The public NOAA window supports fusion.",
        "status": "support",
    }
    campaign["package"]["claims"] = [positive_claim]
    campaign["report"]["claims"] = [positive_claim]

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )

    assert audit["status"] == "failed"
    assert audit["claimAudits"][0]["admissibility"] == "rejected"
    assert audit["claimAudits"][0]["positiveFusionClaim"] is True
    assert any("positive fusion support" in reason for reason in audit["failureReasons"])
    with pytest.raises(ValueError, match="positive fusion support"):
        op.build_observation_lineage_audit(
            campaign,
            snapshot,
            run_id="OPR-20260613-000001",
            run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
            partition_id="late-mixed",
            time_window=[14400.0, 21360.0],
            artifact_records=_artifact_records(),
        )


def test_observation_lineage_audit_claim_rows_carry_statement_and_reject_inconsistent_positive_flag() -> None:
    snapshot, campaign = _late_campaign()
    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )

    assert audit["claimAudits"][0]["statement"] == campaign["package"]["claims"][0]["statement"]
    assert audit["claimAudits"][0]["claimSource"] == "InvestigationPackage.claims"

    audit["claimAudits"][0]["claimType"] = "fusion_status"
    audit["claimAudits"][0]["claimStatus"] = "support"
    audit["claimAudits"][0]["statement"] = "Fusion is occurring"
    audit["claimAudits"][0]["positiveFusionClaim"] = False
    audit["claimAudits"][0]["admissibility"] = "admissible"

    with pytest.raises(ValueError, match="positiveFusionClaim"):
        op.validate_observation_lineage_audit(audit)


def test_observation_lineage_audit_rejects_unknown_claim_artifact_evidence() -> None:
    snapshot, campaign = _late_campaign()
    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["claimAudits"][0]["evidenceArtifactIds"] = ["ghost-diagnostic-artifact"]

    with pytest.raises(ValueError, match="unknown diagnostic artifact"):
        op.validate_observation_lineage_audit(audit, require_passed=False)


def test_observation_lineage_audit_rejects_runstore_ref_missing_path_or_sha256() -> None:
    snapshot, campaign = _late_campaign()
    artifact_records = {
        "public_snapshot": {
            "name": "public_snapshot",
            "type": "public_observation_snapshot",
            "path": None,
            "sha256": "0" * 64,
            "artifactId": "OPA-20260613-000001",
        },
        "source_provenance": {
            "name": "source_provenance",
            "type": "source_provenance",
            "path": "artifacts/source-provenance.json",
            "sha256": None,
            "artifactId": "OPA-20260613-000002",
        },
    }

    with pytest.raises(ValueError, match="path"):
        op.build_observation_lineage_audit(
            campaign,
            snapshot,
            run_id="OPR-20260613-000001",
            run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
            partition_id="late-mixed",
            time_window=[14400.0, 21360.0],
            artifact_records=artifact_records,
            fail_on_error=False,
        )

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["sourceRefs"][0].update(
        {
            "artifactName": "public_snapshot",
            "artifactType": "public_observation_snapshot",
            "path": None,
            "sha256": "0" * 64,
            "runArtifactId": "OPA-20260613-000001",
        }
    )
    with pytest.raises(ValueError, match="path"):
        op.validate_observation_lineage_audit(audit, require_passed=False)

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["transformRefs"][0].update(
        {
            "artifactName": "signal_index",
            "artifactType": "signal_channel_index",
            "path": "artifacts/signal-index.json",
            "sha256": None,
            "runArtifactId": "OPA-20260613-000003",
        }
    )
    with pytest.raises(ValueError, match="sha256"):
        op.validate_observation_lineage_audit(audit, require_passed=False)


def test_observation_lineage_audit_rejects_ghost_source_and_signal_edges() -> None:
    snapshot, campaign = _late_campaign()

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["diagnosticArtifactRefs"][0]["sourceRefIds"] = ["ghost-source"]
    with pytest.raises(ValueError, match="unknown sourceRef"):
        op.validate_observation_lineage_audit(audit, require_passed=False)

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["diagnosticArtifactRefs"][0]["signalIds"] = ["ghost-signal"]
    with pytest.raises(ValueError, match="unknown signal"):
        op.validate_observation_lineage_audit(audit, require_passed=False)

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["mediatedReadoutRefs"][0]["signalId"] = "ghost-signal"
    with pytest.raises(ValueError, match="unknown signal"):
        op.validate_observation_lineage_audit(audit, require_passed=False)

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["spectrumLineage"][0]["sourceSignalId"] = "ghost-signal"
    with pytest.raises(ValueError, match="unknown source signal"):
        op.validate_observation_lineage_audit(audit, require_passed=False)


def test_observation_lineage_audit_rejects_structurally_incomplete_nested_rows() -> None:
    snapshot, campaign = _late_campaign()

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["spectrumLineage"][0]["status"] = "computed"
    del audit["spectrumLineage"][0]["method"]
    with pytest.raises(ValueError, match="method"):
        op.validate_observation_lineage_audit(audit, require_passed=False)

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    del audit["fusionAssessment"]["requiredProductObservables"]
    with pytest.raises(ValueError, match="requiredProductObservables"):
        op.validate_observation_lineage_audit(audit, require_passed=False)

    audit = op.build_observation_lineage_audit(
        campaign,
        snapshot,
        run_id="OPR-20260613-000001",
        run_group_id="public-observation-lineage-audit-noaa-swpc-l1-6h-20260612",
        partition_id="late-mixed",
        time_window=[14400.0, 21360.0],
        artifact_records=_artifact_records(),
        fail_on_error=False,
    )
    audit["spectrumLineage"][0]["status"] = "not_computed"
    audit["spectrumLineage"][0]["supportsPositiveFusionInference"] = True
    with pytest.raises(ValueError, match="cannot support positive fusion inference"):
        op.validate_observation_lineage_audit(audit, require_passed=False)
