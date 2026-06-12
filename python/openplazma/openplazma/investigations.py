from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._json import load_json, save_json
from ._validation import require_finite_number, require_iso_datetime, require_keys, require_list, require_mapping, require_string

VERSION = "0.1.0"

TARGET_KINDS = {
    "lab_plasma",
    "fusion_device",
    "atmospheric_light",
    "organism",
    "organism_interior",
    "artifact",
    "spacecraft",
    "stellar_object",
    "unknown",
}
CANDIDATE_ENERGY_SOURCES = {
    "chemical_luminescence",
    "combustion",
    "electrical_discharge",
    "external_field",
    "plasma",
    "fusion",
    "metabolism",
    "radioactive_decay",
    "sensor_artifact",
    "reflection",
    "unknown",
}
QUESTION_KINDS = {
    "energy_source_classification",
    "is_plasma",
    "is_fusion",
    "fusion_conditions",
    "plasma_maintenance",
}
ARTIFACT_KINDS = {
    "signal_series",
    "spectrum",
    "image_frame",
    "thermal_map",
    "tomographic_volume",
    "field_map",
    "magnetogram",
    "particle_flux",
    "neutron_flux",
    "gamma_spectrum",
    "neutrino_flux",
    "gravity_trace",
    "pressure_trace",
    "acoustic_trace",
    "helioseismic_trace",
    "composition_profile",
    "event_log",
    "motion_track",
}
PROVENANCE_KINDS = {"measured", "derived", "synthetic", "testimony", "unknown"}
INSTRUMENT_KINDS = {
    "human_eye",
    "visible_camera",
    "infrared_camera",
    "ultraviolet_camera",
    "xray_detector",
    "spectrometer",
    "photodiode",
    "bolometer",
    "current_probe",
    "magnetic_probe",
    "electric_probe",
    "interferometer",
    "particle_detector",
    "neutron_detector",
    "gamma_detector",
    "neutrino_detector",
    "gravimeter",
    "accelerometer",
    "pressure_sensor",
    "microphone",
    "tomography_pipeline",
    "helioseismology_pipeline",
    "simulation_diagnostic",
    "unknown",
}
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
CALIBRATION_STATUSES = {"calibrated", "estimated", "uncalibrated", "unknown"}
CONTRIBUTION_KINDS = {
    "thermal_emission",
    "plasma_emission",
    "fusion_product",
    "thermal_coupling",
    "photoelectric_coupling",
    "magnetic_coupling",
    "electric_coupling",
    "gravity_coupling",
    "pressure_coupling",
    "chemical_emission",
    "biological_emission",
    "background",
    "instrument_noise",
    "aliasing_artifact",
    "motion_artifact",
    "reconstruction_artifact",
    "unknown",
}
CONTRIBUTION_ROLES = {"primary", "contaminant", "noise", "candidate", "unknown"}
CONTRIBUTION_STATUSES = {"measured", "inferred", "modeled", "unresolved", "rejected"}
FREQUENCY_DOMAINS = {
    "electromagnetic_carrier",
    "intensity_modulation",
    "acoustic_modulation",
    "motion_modulation",
    "gravity_variation",
    "magnetic_variation",
    "electric_variation",
    "spatial_frequency",
    "unknown",
}
FREQUENCY_METHODS = {
    "fft",
    "stft",
    "wavelet",
    "periodogram",
    "lomb_scargle",
    "harmonic_fit",
    "spectral_line_fit",
    "tomographic_inversion",
    "unknown",
}
FUSION_STATUSES = {"not_assessed", "unknown", "unsupported", "contradicted", "plausible", "supported"}
CONDITION_MODES = {
    "not_applicable",
    "unknown",
    "forward_from_observations",
    "inverse_from_fusion_condition",
}
REACTION_CANDIDATES = {
    "proton_proton_chain",
    "cno_cycle",
    "d_t",
    "d_d",
    "d_he3",
    "p_b11",
    "advanced_aneutronic",
    "unknown",
}
CONDITION_PARAMETERS = {
    "ion_temperature",
    "electron_temperature",
    "density",
    "pressure",
    "confinement_time",
    "triple_product",
    "fuel_mix",
    "composition",
    "ionization_fraction",
    "confinement_mechanism",
    "confinement_geometry",
    "plasma_volume",
    "energy_input",
    "alpha_heating",
    "ash_fraction",
    "gravity",
    "magnetic_field",
    "electric_field",
    "impurity_fraction",
    "radiative_loss",
    "bremsstrahlung_loss",
    "line_radiation_loss",
    "heat_loss",
    "thermal_conduction_loss",
    "particle_loss",
    "neutral_density",
    "material_interaction",
    "plasma_rotation",
    "turbulence_level",
}
CONDITION_STATUSES = {"measured", "inferred", "required", "bounded", "unknown", "contradicted"}
CONDITION_ROLES = {"necessary", "supporting", "contradicting", "unknown"}
CLAIM_TYPES = {"plasma_presence", "fusion_status", "fusion_conditions", "plasma_maintenance", "source_identity"}
CLAIM_STATUSES = {"support", "contradict", "inconclusive", "untested"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _require_kind_version(value: dict[str, Any], kind: str, name: str) -> None:
    require_keys(value, ["kind", "version"], name)
    if value["kind"] != kind:
        raise ValueError(f"{name}.kind must be {kind}.")
    if value["version"] != VERSION:
        raise ValueError(f"{name}.version must be {VERSION}.")


def _require_nonempty_list(value: Any, name: str) -> list[Any]:
    items = require_list(value, name)
    if len(items) == 0:
        raise ValueError(f"{name} must include at least one item.")
    return items


def _require_string_list(value: Any, name: str, *, min_items: int = 0) -> list[str]:
    items = require_list(value, name)
    if len(items) < min_items:
        raise ValueError(f"{name} must include at least {min_items} item(s).")
    for item in items:
        require_string(item, f"{name}[]")
    return items


def _require_enum(value: Any, allowed: set[str], name: str) -> str:
    item = require_string(value, name)
    if item not in allowed:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(allowed))}.")
    return item


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean.")
    return value


def _require_number(value: Any, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    return require_finite_number(value, name, positive=positive, nonnegative=nonnegative)


def _require_optional_number(value: Any, name: str, *, positive: bool = False, nonnegative: bool = False) -> None:
    if value is not None:
        _require_number(value, name, positive=positive, nonnegative=nonnegative)


def _require_datetime_string(value: Any, name: str) -> str:
    return require_iso_datetime(value, name)


def _validate_manifest_path(value: Any, name: str) -> str:
    raw_path = require_string(value, name)
    entry_path = Path(raw_path)
    if entry_path.is_absolute() or "\\" in raw_path or ".." in entry_path.parts or any(":" in part for part in entry_path.parts):
        raise ValueError(f"{name} manifest path must be relative and stay under the repository root.")
    return raw_path


def _resolve_manifest_path(repo_root: str | Path, value: Any, name: str) -> Path:
    raw_path = _validate_manifest_path(value, name)
    root = Path(repo_root).resolve()
    resolved = (root / raw_path).resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"{name} manifest path must stay under the repository root.")
    return resolved


def _validate_region(region: dict[str, Any], name: str) -> None:
    require_keys(region, ["regionId", "label", "description", "limitations"], name)
    require_string(region["regionId"], f"{name}.regionId")
    require_string(region["label"], f"{name}.label")
    require_string(region["description"], f"{name}.description")
    _require_string_list(region["limitations"], f"{name}.limitations", min_items=1)
    if region.get("parentRegionId") is not None:
        require_string(region["parentRegionId"], f"{name}.parentRegionId")


def _validate_target(target: dict[str, Any]) -> set[str]:
    _require_kind_version(target, "openplazma.investigation_target", "InvestigationPackage.target")
    require_keys(
        target,
        ["targetId", "targetKind", "label", "description", "candidateEnergySources", "limitations"],
        "InvestigationPackage.target",
    )
    require_string(target["targetId"], "InvestigationPackage.target.targetId")
    _require_enum(target["targetKind"], TARGET_KINDS, "InvestigationPackage.target.targetKind")
    require_string(target["label"], "InvestigationPackage.target.label")
    require_string(target["description"], "InvestigationPackage.target.description")
    energy_sources = _require_nonempty_list(
        target["candidateEnergySources"],
        "InvestigationPackage.target.candidateEnergySources",
    )
    for index, source in enumerate(energy_sources):
        _require_enum(source, CANDIDATE_ENERGY_SOURCES, f"InvestigationPackage.target.candidateEnergySources[{index}]")
    _require_string_list(target["limitations"], "InvestigationPackage.target.limitations", min_items=1)

    region_ids: set[str] = set()
    regions = require_list(target["regions"], "InvestigationPackage.target.regions") if target.get("regions") is not None else []
    for index, region_ref in enumerate(regions):
        region = require_mapping(region_ref, f"InvestigationPackage.target.regions[{index}]")
        _validate_region(region, f"InvestigationPackage.target.regions[{index}]")
        region_ids.add(region["regionId"])
    for index, region_ref in enumerate(regions):
        region = require_mapping(region_ref, f"InvestigationPackage.target.regions[{index}]")
        parent = region.get("parentRegionId")
        if parent is not None and parent not in region_ids:
            raise ValueError(f"observation region '{region['regionId']}' references unknown parent region '{parent}'.")
    return region_ids


def _validate_question(question: dict[str, Any], name: str) -> None:
    require_keys(question, ["questionId", "questionKind", "text"], name)
    require_string(question["questionId"], f"{name}.questionId")
    _require_enum(question["questionKind"], QUESTION_KINDS, f"{name}.questionKind")
    require_string(question["text"], f"{name}.text")


def _validate_calibration(calibration: dict[str, Any], name: str) -> None:
    require_keys(calibration, ["status", "responseKnown", "correctionApplied", "description", "limitations"], name)
    _require_enum(calibration["status"], CALIBRATION_STATUSES, f"{name}.status")
    _require_bool(calibration["responseKnown"], f"{name}.responseKnown")
    _require_bool(calibration["correctionApplied"], f"{name}.correctionApplied")
    require_string(calibration["description"], f"{name}.description")
    _require_string_list(calibration["limitations"], f"{name}.limitations", min_items=1)


def _validate_instrument(instrument: dict[str, Any], name: str) -> None:
    require_keys(instrument, ["instrumentKind", "label", "observables", "calibration"], name)
    _require_enum(instrument["instrumentKind"], INSTRUMENT_KINDS, f"{name}.instrumentKind")
    require_string(instrument["label"], f"{name}.label")
    for index, observable in enumerate(_require_nonempty_list(instrument["observables"], f"{name}.observables")):
        _require_enum(observable, OBSERVABLES, f"{name}.observables[{index}]")
    _validate_calibration(require_mapping(instrument["calibration"], f"{name}.calibration"), f"{name}.calibration")


def _validate_contribution(contribution: dict[str, Any], name: str) -> None:
    require_keys(contribution, ["contributionKind", "role", "status", "description", "limitations"], name)
    _require_enum(contribution["contributionKind"], CONTRIBUTION_KINDS, f"{name}.contributionKind")
    _require_enum(contribution["role"], CONTRIBUTION_ROLES, f"{name}.role")
    _require_enum(contribution["status"], CONTRIBUTION_STATUSES, f"{name}.status")
    require_string(contribution["description"], f"{name}.description")
    _require_string_list(contribution["limitations"], f"{name}.limitations", min_items=1)


def _validate_frequency_band(band: dict[str, Any], name: str) -> None:
    require_keys(band, ["bandId", "domain", "label", "quantity", "description", "limitations"], name)
    require_string(band["bandId"], f"{name}.bandId")
    _require_enum(band["domain"], FREQUENCY_DOMAINS, f"{name}.domain")
    require_string(band["label"], f"{name}.label")
    _require_optional_number(band.get("lowerFrequencyHz"), f"{name}.lowerFrequencyHz", nonnegative=True)
    _require_optional_number(band.get("upperFrequencyHz"), f"{name}.upperFrequencyHz", positive=True)
    _require_optional_number(band.get("centerFrequencyHz"), f"{name}.centerFrequencyHz", positive=True)
    _require_optional_number(band.get("wavelengthMeters"), f"{name}.wavelengthMeters", positive=True)
    if band.get("lowerFrequencyHz") is not None and band.get("upperFrequencyHz") is not None:
        if float(band["upperFrequencyHz"]) < float(band["lowerFrequencyHz"]):
            raise ValueError(f"{name}.upperFrequencyHz must be greater than or equal to lowerFrequencyHz.")
    require_string(band["quantity"], f"{name}.quantity")
    if band.get("unit") is not None:
        require_string(band["unit"], f"{name}.unit")
    require_string(band["description"], f"{name}.description")
    _require_string_list(band["limitations"], f"{name}.limitations", min_items=1)


def _validate_frequency_peak(peak: dict[str, Any], name: str) -> None:
    require_keys(peak, ["peakId", "frequencyHz", "limitations"], name)
    require_string(peak["peakId"], f"{name}.peakId")
    _require_number(peak["frequencyHz"], f"{name}.frequencyHz", positive=True)
    _require_optional_number(peak.get("amplitude"), f"{name}.amplitude")
    _require_optional_number(peak.get("phaseRadians"), f"{name}.phaseRadians")
    _require_optional_number(peak.get("qualityFactor"), f"{name}.qualityFactor", positive=True)
    _require_optional_number(peak.get("signalToNoiseRatio"), f"{name}.signalToNoiseRatio")
    if peak.get("interpretation") is not None:
        require_string(peak["interpretation"], f"{name}.interpretation")
    _require_string_list(peak["limitations"], f"{name}.limitations", min_items=1)


def _validate_frequency_analysis(analysis: dict[str, Any], name: str) -> None:
    require_keys(
        analysis,
        ["analysisId", "domain", "method", "sourceQuantity", "bands", "peaks", "description", "assumptions", "limitations"],
        name,
    )
    require_string(analysis["analysisId"], f"{name}.analysisId")
    _require_enum(analysis["domain"], FREQUENCY_DOMAINS, f"{name}.domain")
    _require_enum(analysis["method"], FREQUENCY_METHODS, f"{name}.method")
    require_string(analysis["sourceQuantity"], f"{name}.sourceQuantity")
    _require_optional_number(analysis.get("sampleRateHz"), f"{name}.sampleRateHz", positive=True)
    _require_optional_number(analysis.get("windowSeconds"), f"{name}.windowSeconds", positive=True)
    _require_optional_number(analysis.get("frequencyResolutionHz"), f"{name}.frequencyResolutionHz", positive=True)
    bands = require_list(analysis["bands"], f"{name}.bands")
    peaks = require_list(analysis["peaks"], f"{name}.peaks")
    if len(bands) == 0 and len(peaks) == 0:
        raise ValueError(f"{name} requires at least one frequency band or peak.")
    for index, band_ref in enumerate(bands):
        _validate_frequency_band(require_mapping(band_ref, f"{name}.bands[{index}]"), f"{name}.bands[{index}]")
    for index, peak_ref in enumerate(peaks):
        _validate_frequency_peak(require_mapping(peak_ref, f"{name}.peaks[{index}]"), f"{name}.peaks[{index}]")
    require_string(analysis["description"], f"{name}.description")
    _require_string_list(analysis["assumptions"], f"{name}.assumptions")
    _require_string_list(analysis["limitations"], f"{name}.limitations", min_items=1)


def _validate_artifact(artifact: dict[str, Any], name: str, region_ids: set[str]) -> None:
    _require_kind_version(artifact, "openplazma.diagnostic_artifact", name)
    require_keys(artifact, ["artifactId", "artifactKind", "label", "provenanceKind", "description", "limitations"], name)
    require_string(artifact["artifactId"], f"{name}.artifactId")
    _require_enum(artifact["artifactKind"], ARTIFACT_KINDS, f"{name}.artifactKind")
    require_string(artifact["label"], f"{name}.label")
    _require_enum(artifact["provenanceKind"], PROVENANCE_KINDS, f"{name}.provenanceKind")
    if artifact.get("targetRegionId") is not None:
        target_region_id = require_string(artifact["targetRegionId"], f"{name}.targetRegionId")
        if target_region_id not in region_ids:
            raise ValueError(f"diagnostic artifact '{artifact['artifactId']}' references unknown target region '{target_region_id}'.")
    if artifact.get("instrument") is not None:
        _validate_instrument(require_mapping(artifact["instrument"], f"{name}.instrument"), f"{name}.instrument")
    contributions = (
        require_list(artifact["contributions"], f"{name}.contributions")
        if artifact.get("contributions") is not None
        else []
    )
    for index, contribution_ref in enumerate(contributions):
        _validate_contribution(require_mapping(contribution_ref, f"{name}.contributions[{index}]"), f"{name}.contributions[{index}]")
    analyses = (
        require_list(artifact["frequencyAnalyses"], f"{name}.frequencyAnalyses")
        if artifact.get("frequencyAnalyses") is not None
        else []
    )
    for index, analysis_ref in enumerate(analyses):
        _validate_frequency_analysis(
            require_mapping(analysis_ref, f"{name}.frequencyAnalyses[{index}]"),
            f"{name}.frequencyAnalyses[{index}]",
        )
    if artifact.get("sourceUri") is not None:
        require_string(artifact["sourceUri"], f"{name}.sourceUri")
    if artifact.get("signalIds") is not None:
        _require_string_list(artifact["signalIds"], f"{name}.signalIds")
    if artifact.get("quantity") is not None:
        require_string(artifact["quantity"], f"{name}.quantity")
    if artifact.get("unit") is not None:
        require_string(artifact["unit"], f"{name}.unit")
    require_string(artifact["description"], f"{name}.description")
    _require_string_list(artifact["limitations"], f"{name}.limitations", min_items=1)


def _validate_condition_estimate(estimate: dict[str, Any], name: str) -> None:
    require_keys(estimate, ["parameter", "status", "logicalRole", "evidenceArtifactIds", "assumptions", "limitations"], name)
    _require_enum(estimate["parameter"], CONDITION_PARAMETERS, f"{name}.parameter")
    _require_enum(estimate["status"], CONDITION_STATUSES, f"{name}.status")
    _require_enum(estimate["logicalRole"], CONDITION_ROLES, f"{name}.logicalRole")
    for field in ["value", "lowerBound", "upperBound"]:
        _require_optional_number(estimate.get(field), f"{name}.{field}")
    if estimate.get("unit") is not None:
        require_string(estimate["unit"], f"{name}.unit")
    if estimate.get("method") is not None:
        require_string(estimate["method"], f"{name}.method")
    _require_string_list(estimate["evidenceArtifactIds"], f"{name}.evidenceArtifactIds")
    _require_string_list(estimate["assumptions"], f"{name}.assumptions")
    _require_string_list(estimate["limitations"], f"{name}.limitations")


def _validate_fusion_assessment(assessment: dict[str, Any]) -> None:
    name = "InvestigationPackage.fusionAssessment"
    _require_kind_version(assessment, "openplazma.fusion_condition_assessment", name)
    require_keys(
        assessment,
        [
            "assessmentId",
            "fusionStatus",
            "conditionMode",
            "reactionCandidates",
            "observedOrInferredConditions",
            "requiredConditions",
            "unknowns",
            "assumptions",
            "limitations",
        ],
        name,
    )
    require_string(assessment["assessmentId"], f"{name}.assessmentId")
    _require_enum(assessment["fusionStatus"], FUSION_STATUSES, f"{name}.fusionStatus")
    _require_enum(assessment["conditionMode"], CONDITION_MODES, f"{name}.conditionMode")
    for index, reaction in enumerate(_require_nonempty_list(assessment["reactionCandidates"], f"{name}.reactionCandidates")):
        _require_enum(reaction, REACTION_CANDIDATES, f"{name}.reactionCandidates[{index}]")
    for index, estimate_ref in enumerate(require_list(assessment["observedOrInferredConditions"], f"{name}.observedOrInferredConditions")):
        _validate_condition_estimate(
            require_mapping(estimate_ref, f"{name}.observedOrInferredConditions[{index}]"),
            f"{name}.observedOrInferredConditions[{index}]",
        )
    required_conditions = require_list(assessment["requiredConditions"], f"{name}.requiredConditions")
    if assessment["conditionMode"] == "inverse_from_fusion_condition" and len(required_conditions) == 0:
        raise ValueError("inverse fusion-condition assessment requires at least one required condition.")
    for index, estimate_ref in enumerate(required_conditions):
        estimate = require_mapping(estimate_ref, f"{name}.requiredConditions[{index}]")
        _validate_condition_estimate(estimate, f"{name}.requiredConditions[{index}]")
        if estimate["logicalRole"] != "necessary":
            raise ValueError("required fusion conditions must be marked as necessary, not sufficient.")
    if assessment["fusionStatus"] in {"plausible", "supported"} and assessment["conditionMode"] == "not_applicable":
        raise ValueError("plausible or supported fusion status must keep condition assessment open.")
    _require_string_list(assessment["unknowns"], f"{name}.unknowns")
    _require_string_list(assessment["assumptions"], f"{name}.assumptions")
    _require_string_list(assessment["limitations"], f"{name}.limitations", min_items=1)


def _validate_claim(claim: dict[str, Any], name: str) -> None:
    _require_kind_version(claim, "openplazma.investigation_claim", name)
    require_keys(claim, ["claimId", "claimType", "statement", "status", "evidenceArtifactIds", "assumptions", "limitations"], name)
    require_string(claim["claimId"], f"{name}.claimId")
    _require_enum(claim["claimType"], CLAIM_TYPES, f"{name}.claimType")
    require_string(claim["statement"], f"{name}.statement")
    _require_enum(claim["status"], CLAIM_STATUSES, f"{name}.status")
    _require_string_list(claim["evidenceArtifactIds"], f"{name}.evidenceArtifactIds")
    _require_string_list(claim["assumptions"], f"{name}.assumptions")
    _require_string_list(claim["limitations"], f"{name}.limitations")


def _check_artifact_refs(artifact_ids: set[str], ids: list[str], name: str) -> None:
    for artifact_id in ids:
        if artifact_id not in artifact_ids:
            raise ValueError(f"{name} references unknown diagnostic artifact '{artifact_id}'.")


def validate_investigation_package(package: dict[str, Any]) -> dict[str, Any]:
    package = require_mapping(package, "InvestigationPackage")
    _require_kind_version(package, "openplazma.investigation_package", "InvestigationPackage")
    require_keys(
        package,
        ["packageId", "title", "target", "questions", "artifacts", "fusionAssessment", "claims", "limitations"],
        "InvestigationPackage",
    )
    require_string(package["packageId"], "InvestigationPackage.packageId")
    require_string(package["title"], "InvestigationPackage.title")
    region_ids = _validate_target(require_mapping(package["target"], "InvestigationPackage.target"))

    for index, question_ref in enumerate(_require_nonempty_list(package["questions"], "InvestigationPackage.questions")):
        _validate_question(
            require_mapping(question_ref, f"InvestigationPackage.questions[{index}]"),
            f"InvestigationPackage.questions[{index}]",
        )

    artifacts = require_list(package["artifacts"], "InvestigationPackage.artifacts")
    artifact_ids: set[str] = set()
    for index, artifact_ref in enumerate(artifacts):
        artifact = require_mapping(artifact_ref, f"InvestigationPackage.artifacts[{index}]")
        _validate_artifact(artifact, f"InvestigationPackage.artifacts[{index}]", region_ids)
        if artifact["artifactId"] in artifact_ids:
            raise ValueError(f"duplicate diagnostic artifact id '{artifact['artifactId']}'.")
        artifact_ids.add(artifact["artifactId"])

    assessment = require_mapping(package["fusionAssessment"], "InvestigationPackage.fusionAssessment")
    _validate_fusion_assessment(assessment)
    for index, estimate in enumerate(assessment["observedOrInferredConditions"]):
        _check_artifact_refs(
            artifact_ids,
            estimate["evidenceArtifactIds"],
            f"fusionAssessment.observedOrInferredConditions[{index}].evidenceArtifactIds",
        )
    for index, estimate in enumerate(assessment["requiredConditions"]):
        _check_artifact_refs(
            artifact_ids,
            estimate["evidenceArtifactIds"],
            f"fusionAssessment.requiredConditions[{index}].evidenceArtifactIds",
        )

    for index, claim_ref in enumerate(require_list(package["claims"], "InvestigationPackage.claims")):
        claim = require_mapping(claim_ref, f"InvestigationPackage.claims[{index}]")
        _validate_claim(claim, f"InvestigationPackage.claims[{index}]")
        _check_artifact_refs(artifact_ids, claim["evidenceArtifactIds"], f"claims[{index}].evidenceArtifactIds")

    _require_string_list(package["limitations"], "InvestigationPackage.limitations", min_items=1)
    return package


def validate_investigation_fixture_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = require_mapping(manifest, "InvestigationFixtureManifest")
    _require_kind_version(manifest, "openplazma.investigation_fixture_manifest", "InvestigationFixtureManifest")
    require_keys(manifest, ["provider", "datasetId", "packages"], "InvestigationFixtureManifest")
    if manifest["provider"] != "STATIC_FIXTURE":
        raise ValueError("InvestigationFixtureManifest.provider must be STATIC_FIXTURE.")
    require_string(manifest["datasetId"], "InvestigationFixtureManifest.datasetId")
    seen: set[str] = set()
    for index, entry_ref in enumerate(_require_nonempty_list(manifest["packages"], "InvestigationFixtureManifest.packages")):
        entry = require_mapping(entry_ref, f"InvestigationFixtureManifest.packages[{index}]")
        require_keys(entry, ["packageId", "title", "path"], f"InvestigationFixtureManifest.packages[{index}]")
        package_id = require_string(entry["packageId"], f"InvestigationFixtureManifest.packages[{index}].packageId")
        if package_id in seen:
            raise ValueError(f"duplicate investigation package id '{package_id}'.")
        seen.add(package_id)
        require_string(entry["title"], f"InvestigationFixtureManifest.packages[{index}].title")
        _validate_manifest_path(entry["path"], f"InvestigationFixtureManifest.packages[{index}].path")
    return manifest


def validate_investigation_report(report: dict[str, Any], *, package: dict[str, Any] | None = None) -> dict[str, Any]:
    report = require_mapping(report, "InvestigationReport")
    _require_kind_version(report, "openplazma.investigation_report", "InvestigationReport")
    require_keys(
        report,
        ["reportId", "packageId", "createdAt", "claims", "assumptions", "limitations", "nextObservations"],
        "InvestigationReport",
    )
    require_string(report["reportId"], "InvestigationReport.reportId")
    require_string(report["packageId"], "InvestigationReport.packageId")
    _require_datetime_string(report["createdAt"], "InvestigationReport.createdAt")
    claims = _require_nonempty_list(report["claims"], "InvestigationReport.claims")
    for index, claim_ref in enumerate(claims):
        _validate_claim(require_mapping(claim_ref, f"InvestigationReport.claims[{index}]"), f"InvestigationReport.claims[{index}]")
    _require_string_list(report["assumptions"], "InvestigationReport.assumptions")
    _require_string_list(report["limitations"], "InvestigationReport.limitations", min_items=1)
    _require_string_list(report["nextObservations"], "InvestigationReport.nextObservations")

    if package is not None:
        validated_package = validate_investigation_package(package)
        if report["packageId"] != validated_package["packageId"]:
            raise ValueError("InvestigationReport.packageId must match the referenced InvestigationPackage.")
        artifact_ids = {artifact["artifactId"] for artifact in validated_package["artifacts"]}
        for index, claim in enumerate(report["claims"]):
            _check_artifact_refs(artifact_ids, claim["evidenceArtifactIds"], f"claims[{index}].evidenceArtifactIds")
    return report


def load_investigation_package(path: str | Path) -> dict[str, Any]:
    return validate_investigation_package(load_json(path))


def load_investigation_fixture_manifest(path: str | Path) -> dict[str, Any]:
    return validate_investigation_fixture_manifest(load_json(path))


def list_static_investigation_packages(repo_root: str | Path) -> list[dict[str, Any]]:
    manifest_path = Path(repo_root) / "data" / "fixtures" / "static" / "investigations" / "manifest.json"
    manifest = load_investigation_fixture_manifest(manifest_path)
    return list(manifest["packages"])


def load_static_investigation_package(repo_root: str | Path, package_id: str) -> dict[str, Any]:
    for entry in list_static_investigation_packages(repo_root):
        if entry["packageId"] == package_id:
            package = load_investigation_package(
                _resolve_manifest_path(repo_root, entry["path"], f"InvestigationFixtureManifest.package '{package_id}'")
            )
            if package["packageId"] != entry["packageId"]:
                raise ValueError(
                    f"Investigation fixture manifest packageId '{entry['packageId']}' "
                    f"does not match package file packageId '{package['packageId']}'."
                )
            return package
    raise ValueError(f"Investigation package '{package_id}' was not found in STATIC_FIXTURE data.")


def load_investigation_report(path: str | Path, *, package: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate_investigation_report(load_json(path), package=package)


def save_investigation_report(report: dict[str, Any], path: str | Path, *, package: dict[str, Any] | None = None) -> None:
    save_json(validate_investigation_report(report, package=package), path)


def create_investigation_report(
    package: dict[str, Any],
    *,
    claims: list[dict[str, Any]] | None = None,
    report_id: str | None = None,
    created_at: str | None = None,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
    next_observations: list[str] | None = None,
) -> dict[str, Any]:
    validated_package = validate_investigation_package(package)
    selected_claims = [dict(claim) for claim in (claims if claims is not None else validated_package["claims"])]
    unknowns = validated_package["fusionAssessment"]["unknowns"]
    report = {
        "kind": "openplazma.investigation_report",
        "version": VERSION,
        "reportId": report_id or f"report-{validated_package['packageId']}",
        "packageId": validated_package["packageId"],
        "createdAt": created_at or _now(),
        "claims": selected_claims,
        "assumptions": (
            assumptions
            if assumptions is not None
            else ["The supplied investigation package is the evidence set under review."]
        ),
        "limitations": limitations if limitations is not None else list(validated_package["limitations"]),
        "nextObservations": (
            next_observations
            if next_observations is not None
            else [f"Add a calibrated diagnostic for {unknown}." for unknown in unknowns[:3]]
        ),
    }
    return validate_investigation_report(report, package=validated_package)


def summarize_investigation_package(package: dict[str, Any]) -> dict[str, Any]:
    validated_package = validate_investigation_package(package)
    return {
        "packageId": validated_package["packageId"],
        "title": validated_package["title"],
        "targetKind": validated_package["target"]["targetKind"],
        "targetLabel": validated_package["target"]["label"],
        "candidateEnergySources": list(validated_package["target"]["candidateEnergySources"]),
        "fusionStatus": validated_package["fusionAssessment"]["fusionStatus"],
        "conditionMode": validated_package["fusionAssessment"]["conditionMode"],
        "artifactCount": len(validated_package["artifacts"]),
        "artifactIds": [artifact["artifactId"] for artifact in validated_package["artifacts"]],
        "questionKinds": [question["questionKind"] for question in validated_package["questions"]],
        "unknowns": list(validated_package["fusionAssessment"]["unknowns"]),
        "limitations": list(validated_package["limitations"]),
    }
