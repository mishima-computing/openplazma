import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import openplazma as op


REPO_ROOT = Path(__file__).parents[3]
MANIFEST = REPO_ROOT / "data" / "fixtures" / "static" / "investigations" / "manifest.json"


def test_list_static_investigation_packages_from_manifest():
    entries = op.list_static_investigation_packages(REPO_ROOT)

    assert [entry["packageId"] for entry in entries] == [
        "will-o-wisp-001",
        "organism-interior-001",
        "solar-inverse-001",
    ]
    assert op.load_investigation_fixture_manifest(MANIFEST)["provider"] == "STATIC_FIXTURE"


def test_all_static_investigation_packages_validate():
    entries = op.list_static_investigation_packages(REPO_ROOT)

    for entry in entries:
        package = op.load_static_investigation_package(REPO_ROOT, entry["packageId"])
        summary = op.summarize_investigation_package(package)
        assert summary["packageId"] == entry["packageId"]
        assert summary["artifactCount"] == len(package["artifacts"])
        assert summary["candidateEnergySources"]


def test_draft_investigation_package_allows_empty_artifacts():
    package = copy.deepcopy(op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001"))
    package["packageId"] = "draft-empty-artifacts"
    package["artifacts"] = []
    package["observations"] = []
    package["claims"] = []
    package["fusionAssessment"]["assessmentId"] = "draft-empty-artifacts-fusion-assessment"
    package["fusionAssessment"]["observedOrInferredConditions"] = []
    package["fusionAssessment"]["requiredConditions"] = []

    validated = op.validate_investigation_package(package)

    assert op.summarize_investigation_package(validated)["artifactCount"] == 0


def test_static_investigation_manifest_package_id_must_match_loaded_package(tmp_path):
    package = copy.deepcopy(op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001"))
    package["packageId"] = "file-package-id"
    package_path = tmp_path / "data" / "fixtures" / "static" / "investigations" / "mismatch" / "investigation-package.json"
    package_path.parent.mkdir(parents=True)
    package_path.write_text(json.dumps(package), encoding="utf-8")

    manifest = copy.deepcopy(op.load_investigation_fixture_manifest(MANIFEST))
    manifest["packages"] = [
        {
            "packageId": "manifest-package-id",
            "title": "Manifest package ID",
            "path": "data/fixtures/static/investigations/mismatch/investigation-package.json",
        }
    ]
    manifest_path = tmp_path / "data" / "fixtures" / "static" / "investigations" / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest packageId"):
        op.load_static_investigation_package(tmp_path, "manifest-package-id")


def test_static_investigation_manifest_paths_must_stay_under_repo_root(tmp_path):
    manifest = copy.deepcopy(op.load_investigation_fixture_manifest(MANIFEST))
    manifest["packages"] = [
        {
            "packageId": "will-o-wisp-001",
            "title": "Will-o-wisp plasma first-pass investigation",
            "path": str(REPO_ROOT / "data" / "fixtures" / "static" / "investigations" / "will-o-wisp-001" / "investigation-package.json"),
        }
    ]
    manifest_path = tmp_path / "data" / "fixtures" / "static" / "investigations" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest path"):
        op.load_static_investigation_package(tmp_path, "will-o-wisp-001")


def test_will_o_wisp_package_exposes_frequency_and_measurement_gaps():
    package = op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001")

    emission = next(artifact for artifact in package["artifacts"] if artifact["artifactId"] == "emission-timeseries")
    spectrum = next(artifact for artifact in package["artifacts"] if artifact["artifactId"] == "visible-spectrum")

    assert emission["frequencyAnalyses"][0]["domain"] == "intensity_modulation"
    assert spectrum["frequencyAnalyses"][0]["domain"] == "electromagnetic_carrier"
    assert "particle products" in package["fusionAssessment"]["unknowns"]


def test_unknown_artifact_refs_are_rejected():
    package = copy.deepcopy(op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001"))
    package["claims"][0]["evidenceArtifactIds"] = ["missing-artifact"]

    with pytest.raises(ValueError, match="unknown diagnostic artifact"):
        op.validate_investigation_package(package)


def test_mediated_observation_readouts_are_required_for_support_claims():
    package = copy.deepcopy(op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001"))
    package["claims"][0]["evidenceReadoutIds"] = []

    with pytest.raises(ValueError, match="mediated readout"):
        op.validate_investigation_package(package)


def test_human_eye_visible_light_absence_and_simulation_shortcuts_are_rejected():
    package = copy.deepcopy(op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001"))
    package["observations"] = [
        {
            "kind": "openplazma.observation_statement",
            "version": "0.1.0",
            "readoutId": "eye-visible-readout",
            "artifactId": "witness-eye-report",
            "observable": "visible_light",
            "readoutKind": "human_report",
            "method": "unaided_visual_report",
            "status": "detected",
            "assumptions": ["The witness report is sincere."],
            "limitations": ["Human vision is uncalibrated."],
            "alternatives": ["combustion", "reflection"],
        }
    ]
    package["fusionAssessment"]["observedOrInferredConditions"] = []
    package["claims"] = [
        {
            "kind": "openplazma.investigation_claim",
            "version": "0.1.0",
            "claimId": "claim-eye-proves-plasma",
            "claimType": "plasma_presence",
            "statement": "The unaided eye report proves the phenomenon is plasma.",
            "status": "support",
            "evidenceArtifactIds": ["witness-eye-report"],
            "evidenceReadoutIds": ["eye-visible-readout"],
            "method": "visual_identity_shortcut",
            "assumptions": ["Visible glow is plasma."],
            "limitations": ["No calibrated diagnostic."],
            "alternatives": [],
        }
    ]

    with pytest.raises(ValueError, match="human-eye"):
        op.validate_investigation_package(package)

    package = copy.deepcopy(op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001"))
    package["observations"] = [
        {
            "kind": "openplazma.observation_statement",
            "version": "0.1.0",
            "readoutId": "visible-spectrum-readout",
            "artifactId": "visible-spectrum",
            "observable": "visible_light",
            "readoutKind": "spectral_feature",
            "method": "spectral_line_fit",
            "status": "candidate",
            "assumptions": ["The feature is stable."],
            "limitations": ["Visible light alone does not identify plasma or fusion."],
            "alternatives": ["chemical emission"],
        }
    ]
    package["fusionAssessment"]["observedOrInferredConditions"] = []
    package["claims"] = [
        {
            "kind": "openplazma.investigation_claim",
            "version": "0.1.0",
            "claimId": "claim-visible-proves-fusion",
            "claimType": "fusion_status",
            "statement": "Visible light proves fusion is occurring.",
            "status": "support",
            "evidenceArtifactIds": ["visible-spectrum"],
            "evidenceReadoutIds": ["visible-spectrum-readout"],
            "method": "visible_light_shortcut",
            "assumptions": ["Visible light is a fusion signature."],
            "limitations": ["No product diagnostics."],
            "alternatives": [],
        }
    ]

    with pytest.raises(ValueError, match="visible light"):
        op.validate_investigation_package(package)

    package["claims"][0]["statement"] = "No neutron flux was observed therefore fusion is absent."
    package["claims"][0]["method"] = "absence_shortcut"
    with pytest.raises(ValueError, match="absence"):
        op.validate_investigation_package(package)

    package["artifacts"][1]["provenanceKind"] = "synthetic"
    package["artifacts"][1]["instrument"] = {
        "instrumentKind": "simulation_diagnostic",
        "label": "Synthetic diagnostic",
        "observables": ["visible_light"],
        "calibration": {
            "status": "unknown",
            "responseKnown": False,
            "correctionApplied": False,
            "description": "Synthetic output has no physical instrument response.",
            "limitations": ["Simulation output is not physical observation."],
        },
    }
    package["observations"][0]["artifactId"] = "emission-timeseries"
    package["observations"][0]["readoutId"] = "synthetic-visible-readout"
    package["observations"][0]["readoutKind"] = "model_readout"
    package["claims"][0]["claimType"] = "plasma_presence"
    package["claims"][0]["statement"] = "The simulation observed the phenomenon is plasma."
    package["claims"][0]["evidenceArtifactIds"] = ["emission-timeseries"]
    package["claims"][0]["evidenceReadoutIds"] = ["synthetic-visible-readout"]
    package["claims"][0]["method"] = "simulation_observation_shortcut"
    with pytest.raises(ValueError, match="simulation"):
        op.validate_investigation_package(package)


def test_create_save_and_load_investigation_report_for_notebook(tmp_path):
    package = op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001")
    report = op.create_investigation_report(
        package,
        next_observations=["Add a calibrated current probe and neutron detector before any fusion claim."],
    )
    output = tmp_path / "will-o-wisp-001-investigation-report.json"

    op.save_investigation_report(report, output, package=package)
    loaded = op.load_investigation_report(output, package=package)

    assert loaded["kind"] == "openplazma.investigation_report"
    assert loaded["packageId"] == "will-o-wisp-001"
    assert loaded["claims"][0]["evidenceArtifactIds"]
    assert json.loads(output.read_text(encoding="utf-8"))["reportId"] == "report-will-o-wisp-001"


def test_report_package_mismatch_is_rejected():
    package = op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001")
    report = op.create_investigation_report(package)
    report["packageId"] = "solar-inverse-001"

    with pytest.raises(ValueError, match="packageId"):
        op.validate_investigation_report(report, package=package)


def test_report_timestamp_must_include_timezone():
    package = op.load_static_investigation_package(REPO_ROOT, "will-o-wisp-001")
    report = op.create_investigation_report(package)
    report["createdAt"] = "2026-06-12T00:00:00"

    with pytest.raises(ValueError, match="timezone"):
        op.validate_investigation_report(report, package=package)


def _generic_target() -> dict:
    return {
        "kind": "openplazma.investigation_target",
        "version": "0.1.0",
        "targetId": "external-target",
        "targetKind": "unknown",
        "label": "External target",
        "description": "A target supplied by an external application.",
        "candidateEnergySources": ["unknown", "plasma", "fusion"],
        "limitations": ["External target semantics are supplied outside OpenPlazma."],
    }


def _source_question() -> dict:
    return {
        "questionId": "q-source",
        "questionKind": "energy_source_classification",
        "text": "Which source claim is supported by the evidence?",
    }


def _visible_artifact(artifact_id: str = "visible-image") -> dict:
    return {
        "kind": "openplazma.diagnostic_artifact",
        "version": "0.1.0",
        "artifactId": artifact_id,
        "artifactKind": "image_frame",
        "label": "Visible image frame",
        "provenanceKind": "synthetic",
        "instrument": {
            "instrumentKind": "visible_camera",
            "label": "Visible camera",
            "observables": ["visible_light"],
            "calibration": {
                "status": "uncalibrated",
                "responseKnown": False,
                "correctionApplied": False,
                "description": "Synthetic frame has no calibrated camera response.",
                "limitations": ["Visible intensity is not source-specific."],
            },
        },
        "contributions": [
            {
                "contributionKind": "plasma_emission",
                "role": "candidate",
                "status": "unresolved",
                "description": "Emission could include plasma light.",
                "limitations": ["No line-resolved diagnostic is attached."],
            },
            {
                "contributionKind": "background",
                "role": "contaminant",
                "status": "modeled",
                "description": "Background light can contribute to the frame.",
                "limitations": ["Background subtraction is illustrative."],
            },
        ],
        "description": "Local synthetic visible-light frame for a generic investigation session.",
        "limitations": ["A visible frame cannot identify a source by itself."],
    }


def _visible_observation(artifact_id: str = "visible-image", readout_id: str = "visible-readout") -> dict:
    return {
        "kind": "openplazma.observation_statement",
        "version": "0.1.0",
        "readoutId": readout_id,
        "artifactId": artifact_id,
        "observable": "visible_light",
        "readoutKind": "image_feature",
        "method": "visible_feature_review",
        "status": "candidate",
        "assumptions": ["The frame is the evidence under review."],
        "limitations": ["Visible light alone does not identify plasma or fusion."],
        "alternatives": ["chemical luminescence", "thermal emission", "reflection"],
    }


def _evidence_gap_claim(artifact_id: str = "visible-image", readout_id: str = "visible-readout") -> dict:
    return {
        "kind": "openplazma.investigation_claim",
        "version": "0.1.0",
        "claimId": "claim-visible-only-insufficient",
        "claimType": "fusion_status",
        "statement": "Visible-only evidence does not support a fusion claim.",
        "status": "support",
        "evidenceArtifactIds": [artifact_id],
        "evidenceReadoutIds": [readout_id],
        "method": "evidence_gap_review",
        "assumptions": [],
        "limitations": ["No particle-product diagnostic is attached."],
        "alternatives": ["chemical luminescence", "thermal emission", "reflection"],
    }


def _generic_package() -> dict:
    return op.build_investigation_package(
        package_id="external-session-001",
        title="External investigation session",
        target=_generic_target(),
        questions=[_source_question()],
    )


def test_python_investigation_session_lifecycle_assesses_and_reports(tmp_path):
    package = _generic_package()
    session = op.create_investigation_session(
        session_id="session-external-001",
        package=package,
        required_observables=["visible_light", "electric_current", "neutron_flux"],
        created_at="2026-06-13T00:00:00.000Z",
    )

    with_artifact = op.add_diagnostic_artifact(session, _visible_artifact(), "2026-06-13T00:01:00.000Z")
    with_readout = op.add_observation_statement(
        with_artifact,
        _visible_observation(),
        "2026-06-13T00:01:30.000Z",
    )
    with_claim = op.add_investigation_claim(
        with_readout,
        _evidence_gap_claim(),
        "2026-06-13T00:02:00.000Z",
    )

    assessment = op.assess_investigation_session(with_claim)
    report = op.create_investigation_session_report(
        with_claim,
        created_at="2026-06-13T00:03:00.000Z",
    )
    reported = op.record_investigation_report(with_claim, report, "2026-06-13T00:04:00.000Z")
    output = tmp_path / "session.json"
    op.save_investigation_session(reported, output)

    assert session["status"] == "collecting_evidence"
    assert with_claim["status"] == "ready_for_report"
    assert assessment["readyForReport"] is True
    assert assessment["measurementAssessment"]["missingObservables"] == ["electric_current", "neutron_flux"]
    assert assessment["measurementAssessment"]["artifactAssessments"][0]["identifiability"] == "source_identity_not_supported"
    assert "neutron_flux" in " ".join(report["nextObservations"])
    assert reported["status"] == "reported"
    assert op.load_investigation_session(output)["reports"][0]["reportId"] == report["reportId"]


def test_investigation_session_validation_rejects_bad_boundaries():
    package = op.build_investigation_package(
        package_id="boundary-test",
        title="Boundary test",
        target=_generic_target(),
        questions=[_source_question()],
        artifacts=[_visible_artifact()],
    )
    session = op.create_investigation_session(
        session_id="session-boundary-test",
        package=package,
        created_at="2026-06-13T00:00:00.000Z",
    )

    with pytest.raises(ValueError, match="reported"):
        op.create_investigation_session(
            session_id="session-reported-without-report",
            package=package,
            status="reported",
            created_at="2026-06-13T00:00:00.000Z",
        )

    with pytest.raises(ValueError, match="unknown diagnostic artifact"):
        op.add_investigation_claim(
            session,
            {
                **_evidence_gap_claim("missing-artifact"),
                "evidenceReadoutIds": [],
            },
        )

    with pytest.raises(ValueError, match="mediated readout"):
        op.add_investigation_claim(
            session,
            {
                **_evidence_gap_claim(),
                "evidenceReadoutIds": [],
            },
        )

    with pytest.raises(ValueError, match="packageId"):
        op.record_investigation_report(
            session,
            {
                "kind": "openplazma.investigation_report",
                "version": "0.1.0",
                "reportId": "wrong-package-report",
                "packageId": "other-package",
                "createdAt": "2026-06-13T00:01:00.000Z",
                "claims": [_evidence_gap_claim()],
                "assumptions": [],
                "limitations": ["Wrong package boundary."],
                "nextObservations": [],
            },
        )


def test_log_investigation_session_writes_stable_runstore_artifact_types(tmp_path):
    package = _generic_package()
    session = op.create_investigation_session(
        session_id="session-runstore-test",
        package=package,
        required_observables=["visible_light", "neutron_flux"],
        created_at="2026-06-13T00:00:00.000Z",
    )
    session = op.add_diagnostic_artifact(session, _visible_artifact(), "2026-06-13T00:01:00.000Z")
    session = op.add_observation_statement(session, _visible_observation(), "2026-06-13T00:01:30.000Z")
    session = op.add_investigation_claim(session, _evidence_gap_claim(), "2026-06-13T00:02:00.000Z")
    report = op.create_investigation_session_report(session, created_at="2026-06-13T00:03:00.000Z")
    session = op.record_investigation_report(session, report, "2026-06-13T00:04:00.000Z")
    run_store = tmp_path / ".openplazma"

    with op.start_run(
        project="openplazma-python-sdk",
        campaign="investigation-session",
        run_type="investigation_session",
        run_store=run_store,
    ) as run:
        artifacts = op.log_investigation_session(run, session)
        run_id = run.run_id

    manifest = op.load_manifest(run_id, run_store=run_store)
    assert list(artifacts) == [
        "investigation_package",
        "investigation_session",
        "investigation_assessment",
        "investigation_report",
    ]
    assert [artifact["name"] for artifact in manifest["artifacts"]] == list(artifacts)
    assert [artifact["type"] for artifact in manifest["artifacts"]] == list(artifacts)
    assert op.load_run(run_id, run_store=run_store)["capabilities"]["controlFacility"] is False


def test_investigation_session_example_script_runs(tmp_path):
    run_store = tmp_path / ".openplazma"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run-investigation-session.py",
            "--run-store",
            str(run_store),
            "--clean",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "OpenPlazma investigation session run" in completed.stdout
    runs = op.list_runs(run_store=run_store)
    assert len(runs) == 1
    manifest = op.load_manifest(runs[0]["runId"], run_store=run_store)
    assert [artifact["type"] for artifact in manifest["artifacts"]] == [
        "investigation_package",
        "investigation_session",
        "investigation_assessment",
        "investigation_report",
    ]
