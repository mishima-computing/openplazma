from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_SDK_ROOT = REPO_ROOT / "python" / "openplazma"
if str(PYTHON_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_SDK_ROOT))

import openplazma as op  # noqa: E402


def _target() -> dict:
    return {
        "kind": "openplazma.investigation_target",
        "version": "0.1.0",
        "targetId": "local-external-target",
        "targetKind": "unknown",
        "label": "Local external target",
        "description": "A neutral target supplied by a local Python investigation workflow.",
        "candidateEnergySources": ["unknown", "plasma", "fusion"],
        "limitations": ["Target semantics are supplied outside OpenPlazma."],
    }


def _question() -> dict:
    return {
        "questionId": "q-source",
        "questionKind": "energy_source_classification",
        "text": "Which source claim is supported by the supplied evidence?",
    }


def _visible_artifact() -> dict:
    return {
        "kind": "openplazma.diagnostic_artifact",
        "version": "0.1.0",
        "artifactId": "visible-frame",
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
                "description": "Local example frame has no calibrated instrument response.",
                "limitations": ["Visible intensity is not source-specific."],
            },
        },
        "contributions": [
            {
                "contributionKind": "plasma_emission",
                "role": "candidate",
                "status": "unresolved",
                "description": "The visible emission could include plasma light.",
                "limitations": ["No line-resolved diagnostic is attached."],
            },
            {
                "contributionKind": "background",
                "role": "contaminant",
                "status": "modeled",
                "description": "Background light can contribute to the frame.",
                "limitations": ["Background separation is illustrative."],
            },
        ],
        "description": "Synthetic visible-light frame for a local investigation session example.",
        "limitations": ["A visible frame cannot identify a source by itself."],
    }


def _visible_readout() -> dict:
    return {
        "kind": "openplazma.observation_statement",
        "version": "0.1.0",
        "readoutId": "visible-readout",
        "artifactId": "visible-frame",
        "observable": "visible_light",
        "readoutKind": "image_feature",
        "method": "visible_feature_review",
        "status": "candidate",
        "assumptions": ["The visible frame is the evidence under review."],
        "limitations": ["Visible light alone does not identify plasma or fusion."],
        "alternatives": ["chemical luminescence", "thermal emission", "reflection"],
    }


def _claim() -> dict:
    return {
        "kind": "openplazma.investigation_claim",
        "version": "0.1.0",
        "claimId": "claim-visible-only-insufficient",
        "claimType": "fusion_status",
        "statement": "Visible-only evidence does not support a fusion claim.",
        "status": "support",
        "evidenceArtifactIds": ["visible-frame"],
        "evidenceReadoutIds": ["visible-readout"],
        "method": "evidence_gap_review",
        "assumptions": [],
        "limitations": ["No particle-product diagnostic is attached."],
        "alternatives": ["chemical luminescence", "thermal emission", "reflection"],
    }


def build_reported_session() -> tuple[dict, dict]:
    package = op.build_investigation_package(
        package_id="local-investigation-session-001",
        title="Local investigation session",
        target=_target(),
        questions=[_question()],
    )
    session = op.create_investigation_session(
        session_id="session-local-investigation-001",
        package=package,
        required_observables=["visible_light", "electric_current", "neutron_flux"],
    )
    session = op.add_diagnostic_artifact(session, _visible_artifact())
    session = op.add_observation_statement(session, _visible_readout())
    session = op.add_investigation_claim(session, _claim())
    report = op.create_investigation_session_report(session)
    return op.record_investigation_report(session, report), report


def main(run_store: str | Path | None = None) -> str:
    selected_run_store = Path(run_store or os.environ.get("OPENPLAZMA_RUN_STORE", ".openplazma"))
    session, report = build_reported_session()
    assessment = op.assess_investigation_session(session)

    with op.start_run(
        project="openplazma-python-sdk",
        campaign="investigation-session",
        run_type="investigation_session",
        config={"source": "notebooks/examples/investigation_session_run.py"},
        run_store=selected_run_store,
    ) as run:
        op.log_investigation_session(run, session, assessment=assessment, report=report)
        run.log_metric("missing_required_observable_count", len(assessment["measurementAssessment"]["missingObservables"]))
        run.log_metric("investigation_report_count", assessment["reportCount"])
        run_id = run.run_id
        output_path = op.runstore_output_hint(run)

    print(f"OpenPlazma investigation session run {run_id} written to {output_path}")
    print("Logged artifacts: investigation_package, investigation_session, investigation_assessment, investigation_report")
    return run_id


if __name__ == "__main__":
    main()
