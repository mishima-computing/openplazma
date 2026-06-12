import copy
import json
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
