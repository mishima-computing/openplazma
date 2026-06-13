from __future__ import annotations

from copy import deepcopy
from pathlib import PurePosixPath
import re
from typing import Any, Sequence

from ._validation import require_keys, require_list, require_mapping, require_string

VERSION = "0.1.0"
KIND = "openplazma.observation_lineage_audit"
AUDIT_STATUSES = {"passed", "failed"}
CLAIM_ADMISSIBILITY_STATUSES = {"admissible", "rejected"}
SPECTRUM_STATUSES = {"computed", "not_computed"}
TRANSFORM_STATUSES = {"computed", "not_computed", "carried_forward"}
SOURCE_KINDS = {"public_snapshot", "source_provenance"}
OBSERVABLES = {
    "visible_light",
    "infrared_light",
    "ultraviolet_light",
    "xray",
    "gamma_ray",
    "heat",
    "electric_current",
    "magnetic_field",
    "electric_field",
    "particle_flux",
    "neutron_flux",
    "neutrino_flux",
    "gravity",
    "pressure",
    "acoustic_wave",
    "motion",
    "composition",
    "density",
    "temperature",
    "unknown",
}
READOUT_KINDS = {
    "raw_sample",
    "summary_statistic",
    "frequency_band",
    "frequency_peak",
    "spectral_feature",
    "image_feature",
    "thermal_feature",
    "field_feature",
    "particle_count",
    "absence_statement",
    "human_report",
    "model_readout",
    "unknown",
}
READOUT_STATUSES = {"detected", "not_detected", "candidate", "inconclusive", "unknown"}
CALIBRATION_STATUSES = {"calibrated", "estimated", "uncalibrated", "unknown"}
FUSION_STATUSES = {"not_assessed", "unknown", "unsupported", "contradicted", "plausible", "supported"}
CLAIM_TYPES = {"plasma_presence", "fusion_status", "fusion_conditions", "plasma_maintenance", "source_identity"}
CLAIM_STATUSES = {"support", "contradict", "inconclusive", "untested"}
CLAIM_SOURCES = {"InvestigationPackage.claims", "InvestigationReport.claims"}
PRODUCT_OBSERVABLES = {"neutron_flux", "gamma_ray"}
CONDITION_OBSERVABLES = {"temperature", "density", "ion_temperature", "confinement_time"}
RUNSTORE_ARTIFACT_REF_FIELDS = ("artifactName", "artifactType", "path", "sha256", "runArtifactId")
_RUN_ARTIFACT_ID_RE = re.compile(r"^OPA-\d{8}-\d{6}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _require_kind_version(value: dict[str, Any], kind: str, name: str) -> None:
    require_keys(value, ["kind", "version"], name)
    if value["kind"] != kind:
        raise ValueError(f"{name}.kind must be {kind}.")
    if value["version"] != VERSION:
        raise ValueError(f"{name}.version must be {VERSION}.")


def _require_enum(value: Any, allowed: set[str], name: str) -> str:
    selected = require_string(value, name)
    if selected not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}.")
    return selected


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean.")
    return value


def _require_string_list(value: Any, name: str, *, min_items: int = 0) -> list[str]:
    items = require_list(value, name)
    if len(items) < min_items:
        raise ValueError(f"{name} must contain at least {min_items} item(s).")
    selected = []
    for index, item in enumerate(items):
        selected.append(require_string(item, f"{name}[{index}]"))
    return selected


def _require_ref_list(value: Any, name: str, *, min_items: int = 0) -> list[dict[str, Any]]:
    items = require_list(value, name)
    if len(items) < min_items:
        raise ValueError(f"{name} must contain at least {min_items} item(s).")
    return [require_mapping(item, f"{name}[{index}]") for index, item in enumerate(items)]


def _validate_runstore_artifact_path(path: str, name: str) -> None:
    parsed = PurePosixPath(path)
    if (
        path.startswith("/")
        or "\\" in path
        or len(parsed.parts) < 2
        or parsed.parts[0] != "artifacts"
        or ".." in parsed.parts
        or any(":" in part for part in parsed.parts)
    ):
        raise ValueError(f"{name} must be a relative path under artifacts/.")


def _require_runstore_artifact_ref(ref: dict[str, Any], name: str) -> None:
    artifact_name = require_string(ref.get("artifactName"), f"{name}.artifactName")
    artifact_type = require_string(ref.get("artifactType"), f"{name}.artifactType")
    path = require_string(ref.get("path"), f"{name}.path")
    sha256 = require_string(ref.get("sha256"), f"{name}.sha256")
    run_artifact_id = require_string(ref.get("runArtifactId"), f"{name}.runArtifactId")
    if not artifact_name or not artifact_type:
        raise ValueError(f"{name} must include non-empty RunStore artifact name and type.")
    _validate_runstore_artifact_path(path, f"{name}.path")
    if _SHA256_RE.fullmatch(sha256) is None:
        raise ValueError(f"{name}.sha256 must be a lowercase SHA-256 hex digest.")
    if _RUN_ARTIFACT_ID_RE.fullmatch(run_artifact_id) is None:
        raise ValueError(f"{name}.runArtifactId must look like OPA-YYYYMMDD-000001.")


def _has_runstore_artifact_ref(ref: dict[str, Any]) -> bool:
    return any(field in ref for field in RUNSTORE_ARTIFACT_REF_FIELDS)


def _time_range(value: Any, name: str) -> list[float]:
    pair = require_list(value, name)
    if len(pair) != 2:
        raise ValueError(f"{name} must be a [start, end] pair.")
    start = pair[0]
    end = pair[1]
    if not isinstance(start, (int, float)) or isinstance(start, bool):
        raise ValueError(f"{name}[0] must be a finite number.")
    if not isinstance(end, (int, float)) or isinstance(end, bool):
        raise ValueError(f"{name}[1] must be a finite number.")
    if float(end) < float(start):
        raise ValueError(f"{name}[1] must be greater than or equal to {name}[0].")
    return [float(start), float(end)]


def _artifact_record_ref(record: dict[str, Any] | None, *, fallback_name: str, fallback_type: str) -> dict[str, Any]:
    if record is None:
        return {}
    ref = {
        "artifactName": require_string(record.get("name"), f"artifact_records.{fallback_name}.name"),
        "artifactType": require_string(record.get("type"), f"artifact_records.{fallback_name}.type"),
        "path": require_string(record.get("path"), f"artifact_records.{fallback_name}.path"),
        "sha256": require_string(record.get("sha256"), f"artifact_records.{fallback_name}.sha256"),
        "runArtifactId": require_string(record.get("artifactId"), f"artifact_records.{fallback_name}.artifactId"),
    }
    _require_runstore_artifact_ref(ref, f"artifact_records.{fallback_name}")
    if ref["artifactName"] != fallback_name or ref["artifactType"] != fallback_type:
        raise ValueError(
            f"artifact_records.{fallback_name} must reference artifact {fallback_name} with type {fallback_type}."
        )
    return ref


def _statement_is_negative_or_insufficient(statement: str) -> bool:
    normalized = " ".join(statement.lower().split())
    markers = [
        "does not support",
        "unsupported",
        "not proof",
        "not prove",
        "cannot identify",
        "cannot prove",
        "insufficient",
        "remains untested",
        "not calibrated",
        "no calibrated",
    ]
    return any(marker in normalized for marker in markers)


def _is_positive_fusion_claim(claim: dict[str, Any]) -> bool:
    if claim.get("status") != "support":
        return False
    statement = " ".join(str(claim.get("statement", "")).lower().split())
    if _statement_is_negative_or_insufficient(statement):
        return False
    if claim.get("claimType") == "fusion_status":
        return True
    positive_markers = [
        "fusion is occurring",
        "is fusion",
        "supports fusion",
        "fusion claim is supported",
        "proves fusion",
        "proof of fusion",
    ]
    return any(marker in statement for marker in positive_markers)


def _artifact_records_by_key(artifact_records: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if artifact_records is None:
        return {}
    selected = require_mapping(artifact_records, "artifact_records")
    return {
        key: require_mapping(value, f"artifact_records.{key}")
        for key, value in selected.items()
    }


def _signal_refs(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    signals = require_list(campaign.get("signals"), "PublicObservationCampaign.signals")
    return [require_mapping(signal, f"PublicObservationCampaign.signals[{index}]") for index, signal in enumerate(signals)]


def _package(campaign: dict[str, Any]) -> dict[str, Any]:
    return require_mapping(campaign.get("package"), "PublicObservationCampaign.package")


def _assessment(campaign: dict[str, Any]) -> dict[str, Any]:
    return require_mapping(campaign.get("assessment"), "PublicObservationCampaign.assessment")


def _build_source_refs(
    snapshot: dict[str, Any],
    artifact_records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    provenance = require_mapping(snapshot.get("provenance"), "PublicObservationSnapshot.provenance")
    raw_files = []
    for index, raw_ref in enumerate(require_list(provenance.get("rawFiles"), "SourceProvenance.rawFiles")):
        raw_file = require_mapping(raw_ref, f"SourceProvenance.rawFiles[{index}]")
        raw_files.append(
            {
                "name": require_string(raw_file.get("name"), f"SourceProvenance.rawFiles[{index}].name"),
                "path": require_string(raw_file.get("path"), f"SourceProvenance.rawFiles[{index}].path"),
                "sha256": require_string(raw_file.get("sha256"), f"SourceProvenance.rawFiles[{index}].sha256"),
                "bytes": raw_file.get("bytes"),
            }
        )
    return [
        {
            "sourceRefId": "public-snapshot",
            "sourceKind": "public_snapshot",
            "datasetId": snapshot.get("datasetId"),
            "shotId": snapshot.get("shotId"),
            "recordPath": snapshot.get("recordPath"),
            "bundleSha256": provenance.get("bundleSha256"),
            **_artifact_record_ref(
                artifact_records.get("public_snapshot"),
                fallback_name="public_snapshot",
                fallback_type="public_observation_snapshot",
            ),
        },
        {
            "sourceRefId": "source-provenance",
            "sourceKind": "source_provenance",
            "provider": snapshot.get("provider"),
            "sourceLabel": provenance.get("sourceLabel"),
            "provenancePath": snapshot.get("provenancePath"),
            "bundleSha256": provenance.get("bundleSha256"),
            "rawFileRefs": raw_files,
            **_artifact_record_ref(
                artifact_records.get("source_provenance"),
                fallback_name="source_provenance",
                fallback_type="source_provenance",
            ),
        },
    ]


def _build_transform_refs(
    campaign: dict[str, Any],
    artifact_records: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    transform_refs = [
        {
            "transformId": "signal-channel-index",
            "transformKind": "signal_channel_index",
            "status": "computed",
            "method": "build_signal_channel_index",
            "sourceRefIds": ["public-snapshot"],
            "inputSignalIds": [signal["signalId"] for signal in _signal_refs(campaign)],
            "limitationReasons": ["Channel index is derived from frozen public snapshot signal metadata."],
            **_artifact_record_ref(
                artifact_records.get("signal_index"),
                fallback_name="signal_index",
                fallback_type="signal_channel_index",
            ),
        }
    ]
    spectrum_lineage = []
    spectra = require_list(campaign.get("spectra"), "PublicObservationCampaign.spectra")
    spectra_by_signal = {
        require_mapping(spectrum, f"PublicObservationCampaign.spectra[{index}]")["sourceSignalId"]: require_mapping(
            spectrum, f"PublicObservationCampaign.spectra[{index}]"
        )
        for index, spectrum in enumerate(spectra)
    }
    for signal in _signal_refs(campaign):
        signal_id = require_string(signal.get("signalId"), "SignalRef.signalId")
        series_transform = {
            "transformId": f"signal-series:{signal_id}",
            "transformKind": "signal_series",
            "status": "carried_forward",
            "method": "frozen_public_snapshot_selection",
            "sourceRefIds": ["public-snapshot", "source-provenance"],
            "inputSignalIds": [signal_id],
            "limitationReasons": ["Signal series is copied from the frozen normalized public observation record."],
            **_artifact_record_ref(
                artifact_records.get(f"signal_series:{signal_id}"),
                fallback_name=f"signal_series_{signal_id}",
                fallback_type="signal_series",
            ),
        }
        transform_refs.append(series_transform)
        spectrum = require_mapping(spectra_by_signal.get(signal_id), f"PublicObservationCampaign.spectra[{signal_id}]")
        spectrum_status = require_string(spectrum.get("status"), f"PublicObservationSpectrum[{signal_id}].status")
        limitation_reasons = [
            require_string(item, f"PublicObservationSpectrum[{signal_id}].limitations[]")
            for item in require_list(spectrum.get("limitations"), f"PublicObservationSpectrum[{signal_id}].limitations")
        ]
        method = "fft" if spectrum_status == "computed" else "unknown"
        spectrum_transform = {
            "transformId": f"signal-spectrum:{signal_id}",
            "transformKind": "signal_spectrum",
            "status": spectrum_status,
            "method": method,
            "sourceRefIds": ["public-snapshot", "source-provenance"],
            "inputSignalIds": [signal_id],
            "limitationReasons": limitation_reasons,
            **_artifact_record_ref(
                artifact_records.get(f"signal_spectrum:{signal_id}"),
                fallback_name=f"signal_spectrum_{signal_id}",
                fallback_type="signal_spectrum",
            ),
        }
        transform_refs.append(spectrum_transform)
        spectrum_lineage.append(
            {
                "spectrumId": spectrum.get("spectrumId"),
                "sourceSignalId": signal_id,
                "status": spectrum_status,
                "method": method,
                "transformRefId": spectrum_transform["transformId"],
                "timeRange": spectrum.get("timeRange"),
                "limitationReasons": limitation_reasons,
                "supportsPositiveFusionInference": False,
            }
        )
    transform_refs.extend(
        [
            {
                "transformId": "investigation-package",
                "transformKind": "investigation_package",
                "status": "computed",
                "method": "build_public_observation_campaign",
                "sourceRefIds": ["public-snapshot", "source-provenance"],
                "inputSignalIds": [signal["signalId"] for signal in _signal_refs(campaign)],
                "limitationReasons": ["Package is conservative evidence review, not fusion validation."],
                **_artifact_record_ref(
                    artifact_records.get("investigation_package"),
                    fallback_name="investigation_package",
                    fallback_type="investigation_package",
                ),
            },
            {
                "transformId": "investigation-report",
                "transformKind": "investigation_report",
                "status": "computed",
                "method": "create_investigation_session_report",
                "sourceRefIds": ["public-snapshot", "source-provenance"],
                "inputSignalIds": [signal["signalId"] for signal in _signal_refs(campaign)],
                "limitationReasons": ["Report preserves unsupported fusion disposition and next-observation gaps."],
                **_artifact_record_ref(
                    artifact_records.get("investigation_report"),
                    fallback_name="investigation_report",
                    fallback_type="investigation_report",
                ),
            },
        ]
    )
    return transform_refs, spectrum_lineage


def _build_diagnostic_refs(package: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for index, artifact_ref in enumerate(require_list(package.get("artifacts"), "InvestigationPackage.artifacts")):
        artifact = require_mapping(artifact_ref, f"InvestigationPackage.artifacts[{index}]")
        signal_ids = list(artifact.get("signalIds") or [])
        instrument = require_mapping(artifact.get("instrument"), f"InvestigationPackage.artifacts[{index}].instrument")
        calibration = require_mapping(instrument.get("calibration"), f"InvestigationPackage.artifacts[{index}].instrument.calibration")
        refs.append(
            {
                "diagnosticArtifactId": artifact.get("artifactId"),
                "artifactKind": artifact.get("artifactKind"),
                "sourceKind": require_mapping(artifact.get("source"), f"InvestigationPackage.artifacts[{index}].source").get("sourceKind"),
                "signalIds": signal_ids,
                "sourceRefIds": ["public-snapshot", "source-provenance"],
                "transformRefIds": [
                    *[f"signal-series:{signal_id}" for signal_id in signal_ids],
                    *[f"signal-spectrum:{signal_id}" for signal_id in signal_ids],
                    "investigation-package",
                ],
                "calibrationStatus": calibration.get("status"),
                "calibrationResponseKnown": calibration.get("responseKnown"),
                "uncertaintyStatus": "not_independently_quantified",
                "limitationReasons": list(artifact.get("limitations") or []),
            }
        )
    return refs


def _build_readout_refs(package: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for index, readout_ref in enumerate(require_list(package.get("observations", []), "InvestigationPackage.observations")):
        readout = require_mapping(readout_ref, f"InvestigationPackage.observations[{index}]")
        signal_id = readout.get("signalId")
        transform_ref_ids = ["investigation-package"]
        if isinstance(signal_id, str):
            transform_ref_ids.extend([f"signal-series:{signal_id}", f"signal-spectrum:{signal_id}"])
        refs.append(
            {
                "readoutId": readout.get("readoutId"),
                "diagnosticArtifactId": readout.get("artifactId"),
                "signalId": signal_id,
                "observable": readout.get("observable"),
                "readoutKind": readout.get("readoutKind"),
                "method": readout.get("method"),
                "status": readout.get("status"),
                "transformRefIds": transform_ref_ids,
                "limitationReasons": list(readout.get("limitations") or []),
            }
        )
    return refs


def _has_calibrated_product_readout(
    readout_ids: Sequence[str],
    readouts_by_id: dict[str, dict[str, Any]],
    artifacts_by_id: dict[str, dict[str, Any]],
) -> bool:
    for readout_id in readout_ids:
        readout = readouts_by_id.get(readout_id)
        if readout is None or readout.get("observable") not in PRODUCT_OBSERVABLES:
            continue
        artifact = artifacts_by_id.get(str(readout.get("artifactId")))
        calibration = require_mapping(
            require_mapping(artifact.get("instrument"), "DiagnosticArtifact.instrument").get("calibration"),
            "DiagnosticArtifact.instrument.calibration",
        ) if artifact is not None and artifact.get("instrument") is not None else {}
        if calibration.get("status") == "calibrated" and calibration.get("responseKnown") is True:
            return True
    return False


def _has_condition_evidence(package: dict[str, Any]) -> bool:
    assessment = require_mapping(package.get("fusionAssessment"), "InvestigationPackage.fusionAssessment")
    for estimate_ref in require_list(
        assessment.get("observedOrInferredConditions"),
        "FusionConditionAssessment.observedOrInferredConditions",
    ):
        estimate = require_mapping(estimate_ref, "FusionConditionAssessment.observedOrInferredConditions[]")
        if estimate.get("parameter") not in CONDITION_OBSERVABLES:
            continue
        if estimate.get("status") not in {"measured", "inferred", "bounded"}:
            continue
        if estimate.get("evidenceReadoutIds"):
            return True
    return False


def _claim_audit_rows(
    package: dict[str, Any],
    spectrum_by_signal: dict[str, dict[str, Any]],
    report: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    artifacts = [require_mapping(item, "InvestigationPackage.artifacts[]") for item in require_list(package.get("artifacts"), "InvestigationPackage.artifacts")]
    readouts = [
        require_mapping(item, "InvestigationPackage.observations[]")
        for item in require_list(package.get("observations", []), "InvestigationPackage.observations")
    ]
    artifacts_by_id = {artifact.get("artifactId"): artifact for artifact in artifacts}
    readouts_by_id = {readout.get("readoutId"): readout for readout in readouts}
    failures: list[str] = []
    rows = []
    has_condition_evidence = _has_condition_evidence(package)
    claim_refs = []
    seen_claims: set[tuple[Any, ...]] = set()
    for source_name, raw_claims in [
        ("InvestigationPackage.claims", package.get("claims")),
        ("InvestigationReport.claims", report.get("claims") if report is not None else []),
    ]:
        for index, claim_ref in enumerate(require_list(raw_claims, source_name)):
            claim = require_mapping(claim_ref, f"{source_name}[{index}]")
            key = (
                claim.get("claimId"),
                claim.get("claimType"),
                claim.get("statement"),
                claim.get("status"),
                tuple(claim.get("evidenceArtifactIds") or []),
                tuple(claim.get("evidenceReadoutIds") or []),
            )
            if key in seen_claims:
                continue
            seen_claims.add(key)
            claim_refs.append((source_name, claim))

    for source_name, claim in claim_refs:
        claim_failures: list[str] = []
        evidence_artifact_ids = list(claim.get("evidenceArtifactIds") or [])
        evidence_readout_ids = list(claim.get("evidenceReadoutIds") or [])
        if claim.get("status") in {"support", "contradict"} and not evidence_readout_ids:
            claim_failures.append(f"claim '{claim.get('claimId')}' requires mediated readout evidence.")
        for artifact_id in evidence_artifact_ids:
            if artifact_id not in artifacts_by_id:
                claim_failures.append(f"claim '{claim.get('claimId')}' references unknown diagnostic artifact '{artifact_id}'.")
        cited_readouts = []
        for readout_id in evidence_readout_ids:
            readout = readouts_by_id.get(readout_id)
            if readout is None:
                claim_failures.append(f"claim '{claim.get('claimId')}' references unknown mediated readout '{readout_id}'.")
                continue
            artifact_id = readout.get("artifactId")
            if artifact_id not in artifacts_by_id:
                claim_failures.append(f"mediated readout '{readout_id}' references unknown diagnostic artifact '{artifact_id}'.")
            signal_id = readout.get("signalId")
            if isinstance(signal_id, str) and signal_id not in spectrum_by_signal:
                claim_failures.append(f"mediated readout '{readout_id}' has no spectrum lineage for signal '{signal_id}'.")
            cited_readouts.append(readout)

        positive_fusion_claim = _is_positive_fusion_claim(claim)
        has_calibrated_product = _has_calibrated_product_readout(evidence_readout_ids, readouts_by_id, artifacts_by_id)
        depends_on_not_computed_spectrum = any(
            spectrum_by_signal.get(str(readout.get("signalId")), {}).get("status") == "not_computed"
            for readout in cited_readouts
        )
        if positive_fusion_claim and (not has_calibrated_product or not has_condition_evidence):
            claim_failures.append(
                f"claim '{claim.get('claimId')}' is positive fusion support without calibrated product and condition readouts."
            )
        if positive_fusion_claim and depends_on_not_computed_spectrum:
            claim_failures.append(
                f"claim '{claim.get('claimId')}' depends on a not_computed spectrum for positive fusion support."
            )

        admissibility = "rejected" if claim_failures else "admissible"
        rows.append(
            {
                "claimId": claim.get("claimId"),
                "claimSource": source_name,
                "claimType": claim.get("claimType"),
                "statement": claim.get("statement"),
                "claimStatus": claim.get("status"),
                "positiveFusionClaim": positive_fusion_claim,
                "evidenceArtifactIds": evidence_artifact_ids,
                "evidenceReadoutIds": evidence_readout_ids,
                "admissibility": admissibility,
                "failureReasons": claim_failures,
            }
        )
        failures.extend(claim_failures)
    return rows, failures


def build_observation_lineage_audit(
    campaign: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    run_id: str,
    run_group_id: str,
    partition_id: str,
    time_window: Sequence[float],
    artifact_records: dict[str, Any] | None = None,
    fail_on_error: bool = True,
) -> dict[str, Any]:
    selected_campaign = require_mapping(deepcopy(campaign), "PublicObservationCampaign")
    selected_snapshot = require_mapping(deepcopy(snapshot), "PublicObservationSnapshot")
    selected_artifact_records = _artifact_records_by_key(artifact_records)
    selected_time_window = _time_range(time_window, "time_window")
    package = _package(selected_campaign)
    source_refs = _build_source_refs(selected_snapshot, selected_artifact_records)
    transform_refs, spectrum_lineage = _build_transform_refs(selected_campaign, selected_artifact_records)
    spectrum_by_signal = {
        require_string(row.get("sourceSignalId"), "ObservationLineageAudit.spectrumLineage[].sourceSignalId"): row
        for row in spectrum_lineage
    }
    diagnostic_refs = _build_diagnostic_refs(package)
    readout_refs = _build_readout_refs(package)
    report = require_mapping(selected_campaign.get("report"), "PublicObservationCampaign.report")
    claim_audits, failures = _claim_audit_rows(package, spectrum_by_signal, report)
    fusion_assessment = require_mapping(package.get("fusionAssessment"), "InvestigationPackage.fusionAssessment")
    measurement_assessment = require_mapping(_assessment(selected_campaign).get("measurementAssessment"), "InvestigationSessionAssessment.measurementAssessment")

    for row in spectrum_lineage:
        if row["status"] not in SPECTRUM_STATUSES:
            failures.append(f"spectrum '{row.get('spectrumId')}' has unsupported status '{row.get('status')}'.")
        if row["status"] == "not_computed":
            if row.get("method") is None or not row.get("limitationReasons"):
                failures.append(f"spectrum '{row.get('spectrumId')}' is not_computed without method and limitation reason.")

    if fusion_assessment.get("fusionStatus") != "unsupported":
        failures.append("public observation lineage audit requires fusionStatus unsupported for this slice.")

    audit = {
        "kind": KIND,
        "version": VERSION,
        "auditId": f"obs-lineage-audit-{partition_id}",
        "runId": run_id,
        "runGroupId": run_group_id,
        "partitionId": partition_id,
        "timeWindow": selected_time_window,
        "sourceRefs": source_refs,
        "transformRefs": transform_refs,
        "diagnosticArtifactRefs": diagnostic_refs,
        "mediatedReadoutRefs": readout_refs,
        "spectrumLineage": spectrum_lineage,
        "claimAudits": claim_audits,
        "calibrationSummary": {
            "status": "unknown",
            "responseKnown": False,
            "correctionApplied": False,
            "limitationReasons": [
                "Frozen public data products do not include an independent instrument response model in OpenPlazma.",
                "Unknown calibration cannot support source identity or positive fusion-condition claims.",
            ],
        },
        "uncertaintySummary": {
            "status": "limited",
            "limitationReasons": [
                "Readout uncertainty is inherited from public products and OpenPlazma normalization.",
                "No independent uncertainty propagation is attached to this audit slice.",
            ],
        },
        "fusionAssessment": {
            "fusionStatus": fusion_assessment.get("fusionStatus"),
            "positiveFusionInference": False,
            "missingObservables": list(measurement_assessment.get("missingObservables") or []),
            "requiredProductObservables": sorted(PRODUCT_OBSERVABLES),
            "requiredConditionObservables": sorted(CONDITION_OBSERVABLES),
        },
        "status": "failed" if failures else "passed",
        "failureReasons": failures,
    }
    validate_observation_lineage_audit(audit, require_passed=fail_on_error)
    return audit


def validate_observation_lineage_audit(
    audit: dict[str, Any],
    *,
    require_passed: bool = True,
) -> dict[str, Any]:
    selected = require_mapping(audit, "ObservationLineageAudit")
    _require_kind_version(selected, KIND, "ObservationLineageAudit")
    require_keys(
        selected,
        [
            "auditId",
            "runId",
            "runGroupId",
            "partitionId",
            "timeWindow",
            "sourceRefs",
            "transformRefs",
            "diagnosticArtifactRefs",
            "mediatedReadoutRefs",
            "spectrumLineage",
            "claimAudits",
            "calibrationSummary",
            "uncertaintySummary",
            "fusionAssessment",
            "status",
            "failureReasons",
        ],
        "ObservationLineageAudit",
    )
    require_string(selected["auditId"], "ObservationLineageAudit.auditId")
    require_string(selected["runId"], "ObservationLineageAudit.runId")
    require_string(selected["runGroupId"], "ObservationLineageAudit.runGroupId")
    require_string(selected["partitionId"], "ObservationLineageAudit.partitionId")
    _time_range(selected["timeWindow"], "ObservationLineageAudit.timeWindow")

    source_refs = _require_ref_list(selected["sourceRefs"], "ObservationLineageAudit.sourceRefs", min_items=1)
    transform_refs = _require_ref_list(selected["transformRefs"], "ObservationLineageAudit.transformRefs", min_items=1)
    diagnostic_refs = _require_ref_list(
        selected["diagnosticArtifactRefs"],
        "ObservationLineageAudit.diagnosticArtifactRefs",
        min_items=1,
    )
    readout_refs = _require_ref_list(selected["mediatedReadoutRefs"], "ObservationLineageAudit.mediatedReadoutRefs")
    spectrum_lineage = _require_ref_list(selected["spectrumLineage"], "ObservationLineageAudit.spectrumLineage", min_items=1)
    claim_audits = _require_ref_list(selected["claimAudits"], "ObservationLineageAudit.claimAudits")
    failure_reasons = _require_string_list(selected["failureReasons"], "ObservationLineageAudit.failureReasons")
    status = _require_enum(selected["status"], AUDIT_STATUSES, "ObservationLineageAudit.status")

    source_ref_ids = {require_string(ref.get("sourceRefId"), "ObservationLineageAudit.sourceRefs[].sourceRefId") for ref in source_refs}
    transform_ref_ids = {
        require_string(ref.get("transformId"), "ObservationLineageAudit.transformRefs[].transformId")
        for ref in transform_refs
    }
    signal_ids: set[str] = set()
    for ref in transform_refs:
        signal_ids.update(
            _require_string_list(ref.get("inputSignalIds", []), "ObservationLineageAudit.transformRefs[].inputSignalIds")
        )
    diagnostic_ids = {
        require_string(ref.get("diagnosticArtifactId"), "ObservationLineageAudit.diagnosticArtifactRefs[].diagnosticArtifactId")
        for ref in diagnostic_refs
    }
    readout_ids = {
        require_string(ref.get("readoutId"), "ObservationLineageAudit.mediatedReadoutRefs[].readoutId")
        for ref in readout_refs
    }

    for index, ref in enumerate(source_refs):
        require_keys(
            ref,
            ["sourceRefId", "sourceKind", "artifactName", "artifactType", "path", "sha256", "runArtifactId"],
            f"ObservationLineageAudit.sourceRefs[{index}]",
        )
        _require_runstore_artifact_ref(ref, f"ObservationLineageAudit.sourceRefs[{index}]")
        _require_enum(ref.get("sourceKind"), SOURCE_KINDS, f"ObservationLineageAudit.sourceRefs[{index}].sourceKind")
        if ref.get("rawFileRefs") is not None:
            for raw_index, raw_ref in enumerate(
                _require_ref_list(ref.get("rawFileRefs"), f"ObservationLineageAudit.sourceRefs[{index}].rawFileRefs")
            ):
                require_string(raw_ref.get("name"), f"ObservationLineageAudit.sourceRefs[{index}].rawFileRefs[{raw_index}].name")
                require_string(raw_ref.get("path"), f"ObservationLineageAudit.sourceRefs[{index}].rawFileRefs[{raw_index}].path")
                sha256 = require_string(raw_ref.get("sha256"), f"ObservationLineageAudit.sourceRefs[{index}].rawFileRefs[{raw_index}].sha256")
                if _SHA256_RE.fullmatch(sha256) is None:
                    raise ValueError(f"ObservationLineageAudit.sourceRefs[{index}].rawFileRefs[{raw_index}].sha256 must be a lowercase SHA-256 hex digest.")
    for index, ref in enumerate(transform_refs):
        require_keys(
            ref,
            [
                "transformId",
                "transformKind",
                "status",
                "method",
                "sourceRefIds",
                "inputSignalIds",
                "limitationReasons",
                "artifactName",
                "artifactType",
                "path",
                "sha256",
                "runArtifactId",
            ],
            f"ObservationLineageAudit.transformRefs[{index}]",
        )
        _require_runstore_artifact_ref(ref, f"ObservationLineageAudit.transformRefs[{index}]")
        _require_enum(ref.get("status"), TRANSFORM_STATUSES, f"ObservationLineageAudit.transformRefs[{index}].status")
        require_string(ref.get("transformKind"), f"ObservationLineageAudit.transformRefs[{index}].transformKind")
        require_string(ref.get("method"), f"ObservationLineageAudit.transformRefs[{index}].method")
        _require_string_list(ref.get("inputSignalIds"), f"ObservationLineageAudit.transformRefs[{index}].inputSignalIds")
        _require_string_list(ref.get("limitationReasons"), f"ObservationLineageAudit.transformRefs[{index}].limitationReasons", min_items=1)

    for index, ref in enumerate(transform_refs):
        for source_ref_id in _require_string_list(ref.get("sourceRefIds"), f"ObservationLineageAudit.transformRefs[{index}].sourceRefIds", min_items=1):
            if source_ref_id not in source_ref_ids:
                raise ValueError(f"transform '{ref.get('transformId')}' references unknown sourceRef '{source_ref_id}'.")
    for index, ref in enumerate(diagnostic_refs):
        require_keys(
            ref,
            [
                "diagnosticArtifactId",
                "artifactKind",
                "sourceKind",
                "signalIds",
                "sourceRefIds",
                "transformRefIds",
                "calibrationStatus",
                "calibrationResponseKnown",
                "uncertaintyStatus",
                "limitationReasons",
            ],
            f"ObservationLineageAudit.diagnosticArtifactRefs[{index}]",
        )
        require_string(ref.get("artifactKind"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].artifactKind")
        require_string(ref.get("sourceKind"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].sourceKind")
        _require_enum(ref.get("calibrationStatus"), CALIBRATION_STATUSES, f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].calibrationStatus")
        _require_bool(ref.get("calibrationResponseKnown"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].calibrationResponseKnown")
        require_string(ref.get("uncertaintyStatus"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].uncertaintyStatus")
        _require_string_list(ref.get("limitationReasons"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].limitationReasons", min_items=1)
        for source_ref_id in _require_string_list(ref.get("sourceRefIds"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].sourceRefIds", min_items=1):
            if source_ref_id not in source_ref_ids:
                raise ValueError(f"diagnostic artifact '{ref.get('diagnosticArtifactId')}' references unknown sourceRef '{source_ref_id}'.")
        for signal_id in _require_string_list(ref.get("signalIds"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].signalIds"):
            if signal_id not in signal_ids:
                raise ValueError(f"diagnostic artifact '{ref.get('diagnosticArtifactId')}' references unknown signal '{signal_id}'.")
        for transform_ref_id in _require_string_list(ref.get("transformRefIds"), f"ObservationLineageAudit.diagnosticArtifactRefs[{index}].transformRefIds", min_items=1):
            if transform_ref_id not in transform_ref_ids:
                raise ValueError(f"diagnostic artifact '{ref.get('diagnosticArtifactId')}' references unknown transform '{transform_ref_id}'.")
    for index, ref in enumerate(readout_refs):
        require_keys(
            ref,
            [
                "readoutId",
                "diagnosticArtifactId",
                "observable",
                "readoutKind",
                "method",
                "status",
                "transformRefIds",
                "limitationReasons",
            ],
            f"ObservationLineageAudit.mediatedReadoutRefs[{index}]",
        )
        _require_enum(ref.get("observable"), OBSERVABLES, f"ObservationLineageAudit.mediatedReadoutRefs[{index}].observable")
        _require_enum(ref.get("readoutKind"), READOUT_KINDS, f"ObservationLineageAudit.mediatedReadoutRefs[{index}].readoutKind")
        require_string(ref.get("method"), f"ObservationLineageAudit.mediatedReadoutRefs[{index}].method")
        _require_enum(ref.get("status"), READOUT_STATUSES, f"ObservationLineageAudit.mediatedReadoutRefs[{index}].status")
        _require_string_list(ref.get("limitationReasons"), f"ObservationLineageAudit.mediatedReadoutRefs[{index}].limitationReasons", min_items=1)
        diagnostic_id = require_string(ref.get("diagnosticArtifactId"), f"ObservationLineageAudit.mediatedReadoutRefs[{index}].diagnosticArtifactId")
        if diagnostic_id not in diagnostic_ids:
            raise ValueError(f"mediated readout '{ref.get('readoutId')}' references unknown diagnostic artifact '{diagnostic_id}'.")
        signal_id = ref.get("signalId")
        if signal_id is not None and require_string(signal_id, f"ObservationLineageAudit.mediatedReadoutRefs[{index}].signalId") not in signal_ids:
            raise ValueError(f"mediated readout '{ref.get('readoutId')}' references unknown signal '{signal_id}'.")
        for transform_ref_id in _require_string_list(ref.get("transformRefIds"), f"ObservationLineageAudit.mediatedReadoutRefs[{index}].transformRefIds", min_items=1):
            if transform_ref_id not in transform_ref_ids:
                raise ValueError(f"mediated readout '{ref.get('readoutId')}' references unknown transform '{transform_ref_id}'.")

    for index, row in enumerate(spectrum_lineage):
        require_keys(
            row,
            [
                "spectrumId",
                "sourceSignalId",
                "status",
                "method",
                "transformRefId",
                "timeRange",
                "limitationReasons",
                "supportsPositiveFusionInference",
            ],
            f"ObservationLineageAudit.spectrumLineage[{index}]",
        )
        _require_enum(row.get("status"), SPECTRUM_STATUSES, f"ObservationLineageAudit.spectrumLineage[{index}].status")
        require_string(row.get("method"), f"ObservationLineageAudit.spectrumLineage[{index}].method")
        _time_range(row.get("timeRange"), f"ObservationLineageAudit.spectrumLineage[{index}].timeRange")
        _require_string_list(row.get("limitationReasons"), f"ObservationLineageAudit.spectrumLineage[{index}].limitationReasons", min_items=1)
        supports_positive_fusion_inference = _require_bool(
            row.get("supportsPositiveFusionInference"),
            f"ObservationLineageAudit.spectrumLineage[{index}].supportsPositiveFusionInference",
        )
        source_signal_id = require_string(row.get("sourceSignalId"), f"ObservationLineageAudit.spectrumLineage[{index}].sourceSignalId")
        if source_signal_id not in signal_ids:
            raise ValueError(f"spectrum '{row.get('spectrumId')}' references unknown source signal '{source_signal_id}'.")
        require_string(row.get("transformRefId"), f"ObservationLineageAudit.spectrumLineage[{index}].transformRefId")
        if row["transformRefId"] not in transform_ref_ids:
            raise ValueError(f"spectrum '{row.get('spectrumId')}' references unknown transform '{row['transformRefId']}'.")
        if row["status"] == "not_computed" and supports_positive_fusion_inference:
            raise ValueError(f"spectrum '{row.get('spectrumId')}' is not_computed and cannot support positive fusion inference.")

    for index, row in enumerate(claim_audits):
        require_keys(
            row,
            [
                "claimId",
                "claimSource",
                "claimType",
                "claimStatus",
                "statement",
                "positiveFusionClaim",
                "evidenceArtifactIds",
                "evidenceReadoutIds",
                "admissibility",
                "failureReasons",
            ],
            f"ObservationLineageAudit.claimAudits[{index}]",
        )
        _require_enum(row.get("admissibility"), CLAIM_ADMISSIBILITY_STATUSES, f"ObservationLineageAudit.claimAudits[{index}].admissibility")
        claim_id = require_string(row.get("claimId"), f"ObservationLineageAudit.claimAudits[{index}].claimId")
        _require_enum(row.get("claimSource"), CLAIM_SOURCES, f"ObservationLineageAudit.claimAudits[{index}].claimSource")
        claim_type = _require_enum(row.get("claimType"), CLAIM_TYPES, f"ObservationLineageAudit.claimAudits[{index}].claimType")
        statement = require_string(row.get("statement"), f"ObservationLineageAudit.claimAudits[{index}].statement")
        claim_status = _require_enum(row.get("claimStatus"), CLAIM_STATUSES, f"ObservationLineageAudit.claimAudits[{index}].claimStatus")
        positive_fusion_claim = _require_bool(
            row.get("positiveFusionClaim"),
            f"ObservationLineageAudit.claimAudits[{index}].positiveFusionClaim",
        )
        recomputed_positive_fusion_claim = _is_positive_fusion_claim(
            {
                "claimType": claim_type,
                "statement": statement,
                "status": claim_status,
            }
        )
        if positive_fusion_claim != recomputed_positive_fusion_claim:
            raise ValueError(f"claim audit '{claim_id}' positiveFusionClaim does not match the stored claim fields.")
        evidence_artifact_ids = _require_string_list(row.get("evidenceArtifactIds"), f"ObservationLineageAudit.claimAudits[{index}].evidenceArtifactIds")
        evidence_readout_ids = _require_string_list(row.get("evidenceReadoutIds"), f"ObservationLineageAudit.claimAudits[{index}].evidenceReadoutIds")
        _require_string_list(row.get("failureReasons"), f"ObservationLineageAudit.claimAudits[{index}].failureReasons")
        for artifact_id in evidence_artifact_ids:
            if artifact_id not in diagnostic_ids:
                raise ValueError(f"claim audit '{row.get('claimId')}' references unknown diagnostic artifact '{artifact_id}'.")
        if row.get("claimStatus") in {"support", "contradict"} and not evidence_readout_ids:
            if row.get("admissibility") != "rejected" or not row.get("failureReasons"):
                raise ValueError(f"claim audit '{row.get('claimId')}' requires mediated readout evidence.")
        for readout_id in evidence_readout_ids:
            if readout_id not in readout_ids:
                raise ValueError(f"claim audit '{row.get('claimId')}' references unknown mediated readout '{readout_id}'.")
        if positive_fusion_claim is True and row.get("admissibility") != "rejected":
            raise ValueError(f"positive fusion claim audit '{row.get('claimId')}' must be rejected for public observation lineage.")

    calibration_summary = require_mapping(selected["calibrationSummary"], "ObservationLineageAudit.calibrationSummary")
    require_keys(
        calibration_summary,
        ["status", "limitationReasons", "responseKnown", "correctionApplied"],
        "ObservationLineageAudit.calibrationSummary",
    )
    require_string(calibration_summary.get("status"), "ObservationLineageAudit.calibrationSummary.status")
    _require_string_list(
        calibration_summary.get("limitationReasons"),
        "ObservationLineageAudit.calibrationSummary.limitationReasons",
        min_items=1,
    )
    _require_bool(calibration_summary.get("responseKnown"), "ObservationLineageAudit.calibrationSummary.responseKnown")
    _require_bool(calibration_summary.get("correctionApplied"), "ObservationLineageAudit.calibrationSummary.correctionApplied")

    uncertainty_summary = require_mapping(selected["uncertaintySummary"], "ObservationLineageAudit.uncertaintySummary")
    require_keys(
        uncertainty_summary,
        ["status", "limitationReasons"],
        "ObservationLineageAudit.uncertaintySummary",
    )
    require_string(uncertainty_summary.get("status"), "ObservationLineageAudit.uncertaintySummary.status")
    _require_string_list(
        uncertainty_summary.get("limitationReasons"),
        "ObservationLineageAudit.uncertaintySummary.limitationReasons",
        min_items=1,
    )

    fusion_assessment = require_mapping(selected["fusionAssessment"], "ObservationLineageAudit.fusionAssessment")
    require_keys(
        fusion_assessment,
        [
            "fusionStatus",
            "positiveFusionInference",
            "missingObservables",
            "requiredProductObservables",
            "requiredConditionObservables",
        ],
        "ObservationLineageAudit.fusionAssessment",
    )
    _require_enum(fusion_assessment.get("fusionStatus"), FUSION_STATUSES, "ObservationLineageAudit.fusionAssessment.fusionStatus")
    _require_bool(fusion_assessment.get("positiveFusionInference"), "ObservationLineageAudit.fusionAssessment.positiveFusionInference")
    _require_string_list(fusion_assessment.get("missingObservables"), "ObservationLineageAudit.fusionAssessment.missingObservables")
    _require_string_list(
        fusion_assessment.get("requiredProductObservables"),
        "ObservationLineageAudit.fusionAssessment.requiredProductObservables",
        min_items=1,
    )
    _require_string_list(
        fusion_assessment.get("requiredConditionObservables"),
        "ObservationLineageAudit.fusionAssessment.requiredConditionObservables",
        min_items=1,
    )
    if fusion_assessment.get("positiveFusionInference") is True:
        not_computed = [row.get("spectrumId") for row in spectrum_lineage if row.get("status") == "not_computed"]
        if not_computed:
            raise ValueError("positive fusion inference cannot depend on not_computed spectra.")

    rejected_claims = [row.get("claimId") for row in claim_audits if row.get("admissibility") == "rejected"]
    if status == "passed" and failure_reasons:
        raise ValueError("ObservationLineageAudit.status passed requires empty failureReasons.")
    if status == "passed" and rejected_claims:
        raise ValueError("ObservationLineageAudit.status passed cannot include rejected claim audits.")
    if status == "failed" and not failure_reasons:
        raise ValueError("ObservationLineageAudit.status failed requires at least one failure reason.")
    if require_passed and status != "passed":
        raise ValueError("Observation lineage audit failed: " + "; ".join(failure_reasons))
    return selected
