from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._json import load_json, save_json
from ._validation import require_iso_datetime, require_keys, require_list, require_mapping, require_string
from .context import _validate_observation, _validate_signal_ref, validate_experiment_context
from .mhd import validate_mhd_analysis_bundle
from .signals import validate_signal_series
from .sources import validate_data_provider, validate_source_ref

DEFAULT_STUDY_LIMITATIONS = [
    "STATIC_FIXTURE data only.",
    "Read-only analysis and decision support.",
    "No command/control path or hazardous operating procedure.",
    "Not a standalone authority for safety-critical operation or reactor design decisions.",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _normalize_observations(observations: list[dict[str, Any] | str] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for observation in observations or []:
        if isinstance(observation, str):
            normalized.append({"text": observation})
        elif isinstance(observation, dict):
            normalized.append(dict(observation))
        else:
            raise ValueError("StudyRecord observations must be strings or JSON objects.")
    return normalized


def _validate_ts_context(context: dict[str, Any]) -> None:
    require_keys(
        context,
        [
            "kind",
            "version",
            "contextId",
            "projectId",
            "datasetId",
            "description",
            "safetyClassification",
            "createdAt",
            "target",
            "source",
            "capabilities",
            "shotRef",
            "signals",
            "observations",
            "limitations",
        ],
        "StudyRecord.context",
    )
    if context["kind"] != "openplazma.experiment_context":
        raise ValueError("StudyRecord.context.kind must be openplazma.experiment_context.")
    if context["version"] != "0.1.0":
        raise ValueError("StudyRecord.context.version must be 0.1.0.")
    require_string(context["contextId"], "StudyRecord.context.contextId")
    require_string(context["projectId"], "StudyRecord.context.projectId")
    require_string(context["datasetId"], "StudyRecord.context.datasetId")
    require_string(context["description"], "StudyRecord.context.description")
    require_iso_datetime(context["createdAt"], "StudyRecord.context.createdAt")
    if context["safetyClassification"] not in {"public-educational-fixture", "read-only-local-signal"}:
        raise ValueError("StudyRecord.context.safetyClassification must be public-educational-fixture or read-only-local-signal.")

    target = require_mapping(context["target"], "StudyRecord.context.target")
    require_keys(target, ["type", "id", "label"], "StudyRecord.context.target")
    if target["type"] not in {"static_fixture", "local_run_store"}:
        raise ValueError("StudyRecord.context.target.type must be static_fixture or local_run_store.")

    source = require_mapping(context["source"], "StudyRecord.context.source")
    validate_source_ref(source, "StudyRecord.context.source")

    capabilities = require_mapping(context["capabilities"], "StudyRecord.context.capabilities")
    require_keys(
        capabilities,
        [
            "readData",
            "writeArtifacts",
            "runSimulation",
            "submitComputeJob",
            "readFacilityTelemetry",
            "controlFacility",
        ],
        "StudyRecord.context.capabilities",
    )
    for field in ["readData", "writeArtifacts"]:
        if capabilities[field] is not True:
            raise ValueError(f"StudyRecord.context.capabilities.{field} must be true.")
    for field in ["runSimulation", "submitComputeJob", "readFacilityTelemetry", "controlFacility"]:
        if capabilities[field] is not False:
            raise ValueError(f"StudyRecord.context.capabilities.{field} must be false.")
    for index, observation_ref in enumerate(require_list(context["observations"], "StudyRecord.context.observations")):
        observation = require_mapping(observation_ref, f"StudyRecord.context.observations[{index}]")
        _validate_observation(observation, f"StudyRecord.context.observations[{index}]")
    limitations = require_list(context["limitations"], "StudyRecord.context.limitations")
    if len(limitations) == 0:
        raise ValueError("StudyRecord.context.limitations must include at least one limitation.")
    for index, limitation in enumerate(limitations):
        require_string(limitation, f"StudyRecord.context.limitations[{index}]")


def _validate_ts_shot(shot: dict[str, Any]) -> None:
    require_keys(
        shot,
        ["kind", "version", "shotId", "displayName", "sourceLabel", "recordedAt", "source", "signalIds", "tags"],
        "StudyRecord.shot",
    )
    if shot["kind"] != "openplazma.shot_metadata":
        raise ValueError("StudyRecord.shot.kind must be openplazma.shot_metadata.")
    if shot["version"] != "0.1.0":
        raise ValueError("StudyRecord.shot.version must be 0.1.0.")
    require_string(shot["shotId"], "StudyRecord.shot.shotId")
    require_string(shot["displayName"], "StudyRecord.shot.displayName")
    require_string(shot["sourceLabel"], "StudyRecord.shot.sourceLabel")
    require_iso_datetime(shot["recordedAt"], "StudyRecord.shot.recordedAt")

    source = require_mapping(shot["source"], "StudyRecord.shot.source")
    require_keys(source, ["kind", "provider", "sourceLabel", "uri", "license"], "StudyRecord.shot.source")
    validate_source_ref(source, "StudyRecord.shot.source")
    require_string(source["kind"], "StudyRecord.shot.source.kind")
    if source["kind"] not in {"fixture", "measured", "derived", "synthetic"}:
        raise ValueError("StudyRecord.shot.source.kind must be fixture, measured, derived, or synthetic.")
    require_string(source["sourceLabel"], "StudyRecord.shot.source.sourceLabel")
    require_string(source["uri"], "StudyRecord.shot.source.uri")
    require_string(source["license"], "StudyRecord.shot.source.license")

    signal_ids = require_list(shot["signalIds"], "StudyRecord.shot.signalIds")
    if len(signal_ids) == 0:
        raise ValueError("StudyRecord.shot.signalIds must include at least one signal id.")
    for signal_id in signal_ids:
        require_string(signal_id, "StudyRecord.shot.signalIds[]")
    for index, tag in enumerate(require_list(shot["tags"], "StudyRecord.shot.tags")):
        require_string(tag, f"StudyRecord.shot.tags[{index}]")


def _validate_notebook_record(record: dict[str, Any]) -> dict[str, Any]:
    require_keys(
        record,
        ["kind", "version", "studyId", "createdAt", "source", "signalsViewed", "observations", "limitations"],
        "StudyRecord",
    )
    if record["kind"] != "openplazma.study_record":
        raise ValueError("StudyRecord.kind must be openplazma.study_record.")
    if record["version"] != "0.1.0":
        raise ValueError("StudyRecord.version must be 0.1.0.")
    require_string(record["studyId"], "StudyRecord.studyId")
    require_iso_datetime(record["createdAt"], "StudyRecord.createdAt")

    source = require_mapping(record["source"], "StudyRecord.source")
    require_keys(source, ["provider", "sourceLabel", "shotId"], "StudyRecord.source")
    validate_source_ref(source, "StudyRecord.source")
    require_string(source["sourceLabel"], "StudyRecord.source.sourceLabel")
    require_string(source["shotId"], "StudyRecord.source.shotId")

    signals_viewed = require_list(record["signalsViewed"], "StudyRecord.signalsViewed")
    if len(signals_viewed) == 0:
        raise ValueError("StudyRecord.signalsViewed must include at least one signal.")
    for index, signal_ref in enumerate(signals_viewed):
        signal = require_mapping(signal_ref, f"StudyRecord.signalsViewed[{index}]")
        _validate_signal_ref(signal, f"StudyRecord.signalsViewed[{index}]")

    observations = require_list(record["observations"], "StudyRecord.observations")
    for index, observation_ref in enumerate(observations):
        observation = require_mapping(observation_ref, f"StudyRecord.observations[{index}]")
        _validate_observation(observation, f"StudyRecord.observations[{index}]")

    limitations = require_list(record["limitations"], "StudyRecord.limitations")
    if len(limitations) == 0:
        raise ValueError("StudyRecord.limitations must include at least one limitation.")
    for limitation in limitations:
        require_string(limitation, "StudyRecord.limitations[]")
    return record


def validate_study_record(record: dict[str, Any]) -> dict[str, Any]:
    _validate_notebook_record(record)
    if "context" not in record:
        return record
    require_keys(record, ["context", "shot", "signals", "shotRef"], "StudyRecord")

    context = require_mapping(record["context"], "StudyRecord.context")
    shot = require_mapping(record["shot"], "StudyRecord.shot")
    signals = require_list(record["signals"], "StudyRecord.signals")
    if len(signals) == 0:
        raise ValueError("StudyRecord.signals must include at least one signal.")

    validate_experiment_context(context)
    _validate_ts_shot(shot)
    shot_ref = require_mapping(record["shotRef"], "StudyRecord.shotRef")
    require_keys(shot_ref, ["provider", "shotId"], "StudyRecord.shotRef")
    validate_data_provider(shot_ref["provider"], "StudyRecord.shotRef.provider")
    require_string(shot_ref["shotId"], "StudyRecord.shotRef.shotId")
    if shot_ref["provider"] != shot["source"]["provider"] or shot_ref["shotId"] != shot["shotId"]:
        raise ValueError("StudyRecord.shotRef must match StudyRecord.shot metadata.")
    if shot_ref["provider"] != record["source"]["provider"] or shot_ref["shotId"] != record["source"]["shotId"]:
        raise ValueError("StudyRecord.shotRef must match StudyRecord.source.")
    signal_ids = set(shot["signalIds"])
    actual_signal_ids: set[str] = set()
    for index, signal in enumerate(signals):
        validated_signal = validate_signal_series(require_mapping(signal, f"StudyRecord.signals[{index}]"))
        actual_signal_ids.add(validated_signal["signalId"])
        if validated_signal["signalId"] not in signal_ids:
            raise ValueError("StudyRecord.signals contains a signal not listed in shot.signalIds.")
    for signal_id in signal_ids:
        if signal_id not in actual_signal_ids:
            raise ValueError(f"StudyRecord.shot.signalIds references missing signal '{signal_id}'.")
    for signal_ref in record["signalsViewed"]:
        if signal_ref["signalId"] not in actual_signal_ids:
            raise ValueError(f"StudyRecord.signalsViewed references missing signal '{signal_ref['signalId']}'.")

    if "mhd" in record and record["mhd"] is not None:
        validate_mhd_analysis_bundle(require_mapping(record["mhd"], "StudyRecord.mhd"), actual_signal_ids)

    return record


def load_study_record(path: str | Path) -> dict[str, Any]:
    return validate_study_record(load_json(path))


def save_study_record(record: dict[str, Any], path: str | Path) -> None:
    save_json(validate_study_record(record), path)


def create_study_record(
    *,
    context: dict[str, Any],
    signals_viewed: list[dict[str, Any]] | None = None,
    observations: list[dict[str, Any] | str] | None = None,
    hypothesis: str | None = None,
    limitations: list[str] | None = None,
    study_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    validated_context = validate_experiment_context(context)
    selected_signals = signals_viewed or validated_context["signals"]
    selected_observations = _normalize_observations(validated_context.get("observations", []))
    selected_observations.extend(_normalize_observations(observations))

    record: dict[str, Any] = {
        "kind": "openplazma.study_record",
        "version": "0.1.0",
        "studyId": study_id or f"{validated_context['contextId']}-study",
        "createdAt": created_at or _now(),
        "source": {
            "provider": validated_context["shotRef"]["provider"],
            "sourceLabel": validated_context["source"]["sourceLabel"],
            "shotId": validated_context["shotRef"]["shotId"],
        },
        "signalsViewed": selected_signals,
        "observations": selected_observations,
        "limitations": limitations if limitations is not None else list(validated_context.get("limitations") or DEFAULT_STUDY_LIMITATIONS),
    }
    for field in ["inspiredBy", "uri", "sha256", "validationStatus"]:
        if validated_context["source"].get(field) is not None:
            record["source"][field] = validated_context["source"][field]
    if hypothesis:
        record["hypothesis"] = hypothesis
    return validate_study_record(record)
