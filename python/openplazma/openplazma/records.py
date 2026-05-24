from __future__ import annotations

from pathlib import Path
from typing import Any

from ._json import load_json, save_json
from ._validation import require_keys, require_list, require_mapping, require_string
from .signals import validate_signal_series


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
    require_string(context["createdAt"], "StudyRecord.context.createdAt")
    if context["safetyClassification"] != "public-educational-fixture":
        raise ValueError("StudyRecord.context.safetyClassification must be public-educational-fixture.")

    target = require_mapping(context["target"], "StudyRecord.context.target")
    require_keys(target, ["type", "id", "label"], "StudyRecord.context.target")
    if target["type"] not in {"static_fixture", "local_run_store"}:
        raise ValueError("StudyRecord.context.target.type must be static_fixture or local_run_store.")

    source = require_mapping(context["source"], "StudyRecord.context.source")
    require_keys(source, ["provider", "sourceLabel"], "StudyRecord.context.source")
    if source["provider"] != "STATIC_FIXTURE":
        raise ValueError("StudyRecord.context.source.provider must be STATIC_FIXTURE.")

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
    require_list(context["observations"], "StudyRecord.context.observations")
    require_list(context["limitations"], "StudyRecord.context.limitations")


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
    require_string(shot["recordedAt"], "StudyRecord.shot.recordedAt")

    source = require_mapping(shot["source"], "StudyRecord.shot.source")
    require_keys(source, ["kind", "provider", "sourceLabel", "uri", "license"], "StudyRecord.shot.source")
    if source["provider"] != "STATIC_FIXTURE":
        raise ValueError("StudyRecord.shot.source.provider must be STATIC_FIXTURE.")
    require_string(source["kind"], "StudyRecord.shot.source.kind")
    require_string(source["sourceLabel"], "StudyRecord.shot.source.sourceLabel")
    require_string(source["uri"], "StudyRecord.shot.source.uri")
    require_string(source["license"], "StudyRecord.shot.source.license")

    signal_ids = require_list(shot["signalIds"], "StudyRecord.shot.signalIds")
    if len(signal_ids) == 0:
        raise ValueError("StudyRecord.shot.signalIds must include at least one signal id.")
    for signal_id in signal_ids:
        require_string(signal_id, "StudyRecord.shot.signalIds[]")
    require_list(shot["tags"], "StudyRecord.shot.tags")


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
    require_string(record["createdAt"], "StudyRecord.createdAt")

    source = require_mapping(record["source"], "StudyRecord.source")
    require_keys(source, ["provider", "sourceLabel", "shotId"], "StudyRecord.source")
    if source["provider"] != "STATIC_FIXTURE":
        raise ValueError("StudyRecord.source.provider must be STATIC_FIXTURE.")
    require_string(source["sourceLabel"], "StudyRecord.source.sourceLabel")
    require_string(source["shotId"], "StudyRecord.source.shotId")

    signals_viewed = require_list(record["signalsViewed"], "StudyRecord.signalsViewed")
    if len(signals_viewed) == 0:
        raise ValueError("StudyRecord.signalsViewed must include at least one signal.")
    for index, signal_ref in enumerate(signals_viewed):
        signal = require_mapping(signal_ref, f"StudyRecord.signalsViewed[{index}]")
        require_keys(signal, ["signalId"], f"StudyRecord.signalsViewed[{index}]")
        require_string(signal["signalId"], f"StudyRecord.signalsViewed[{index}].signalId")

    observations = require_list(record["observations"], "StudyRecord.observations")
    for index, observation_ref in enumerate(observations):
        observation = require_mapping(observation_ref, f"StudyRecord.observations[{index}]")
        require_keys(observation, ["text"], f"StudyRecord.observations[{index}]")
        require_string(observation["text"], f"StudyRecord.observations[{index}].text")

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
    require_keys(record, ["context", "shot", "signals"], "StudyRecord")

    context = require_mapping(record["context"], "StudyRecord.context")
    shot = require_mapping(record["shot"], "StudyRecord.shot")
    signals = require_list(record["signals"], "StudyRecord.signals")
    if len(signals) == 0:
        raise ValueError("StudyRecord.signals must include at least one signal.")

    _validate_ts_context(context)
    _validate_ts_shot(shot)
    signal_ids = set(shot["signalIds"])
    for index, signal in enumerate(signals):
        validated_signal = validate_signal_series(require_mapping(signal, f"StudyRecord.signals[{index}]"))
        if validated_signal["signalId"] not in signal_ids:
            raise ValueError("StudyRecord.signals contains a signal not listed in shot.signalIds.")

    return record


def load_study_record(path: str | Path) -> dict[str, Any]:
    return validate_study_record(load_json(path))


def save_study_record(record: dict[str, Any], path: str | Path) -> None:
    save_json(validate_study_record(record), path)
