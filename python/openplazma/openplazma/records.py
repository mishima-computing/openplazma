from __future__ import annotations

from pathlib import Path
from typing import Any

from ._json import load_json, save_json
from ._validation import require_keys, require_list, require_mapping, require_string
from .signals import validate_signal_series


def _validate_ts_context(context: dict[str, Any]) -> None:
    require_keys(
        context,
        ["projectId", "datasetId", "facility", "description", "safetyClassification", "createdAt"],
        "StudyRecord.context",
    )
    require_string(context["projectId"], "StudyRecord.context.projectId")
    require_string(context["datasetId"], "StudyRecord.context.datasetId")
    require_string(context["facility"], "StudyRecord.context.facility")
    require_string(context["description"], "StudyRecord.context.description")
    require_string(context["createdAt"], "StudyRecord.context.createdAt")
    if context["safetyClassification"] != "public-educational-fixture":
        raise ValueError("StudyRecord.context.safetyClassification must be public-educational-fixture.")


def _validate_ts_shot(shot: dict[str, Any]) -> None:
    require_keys(shot, ["shotId", "displayName", "deviceName", "recordedAt", "source", "signalIds", "tags"], "StudyRecord.shot")
    require_string(shot["shotId"], "StudyRecord.shot.shotId")
    require_string(shot["displayName"], "StudyRecord.shot.displayName")
    require_string(shot["deviceName"], "StudyRecord.shot.deviceName")
    require_string(shot["recordedAt"], "StudyRecord.shot.recordedAt")

    source = require_mapping(shot["source"], "StudyRecord.shot.source")
    require_keys(source, ["kind", "provider", "uri", "license"], "StudyRecord.shot.source")
    if source["provider"] != "STATIC_FIXTURE":
        raise ValueError("StudyRecord.shot.source.provider must be STATIC_FIXTURE for M2.")
    require_string(source["kind"], "StudyRecord.shot.source.kind")
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
    require_string(record["version"], "StudyRecord.version")
    require_string(record["studyId"], "StudyRecord.studyId")
    require_string(record["createdAt"], "StudyRecord.createdAt")

    source = require_mapping(record["source"], "StudyRecord.source")
    require_keys(source, ["provider", "shotId"], "StudyRecord.source")
    if source["provider"] != "STATIC_FIXTURE":
        raise ValueError("StudyRecord.source.provider must be STATIC_FIXTURE for M2.")
    require_string(source["shotId"], "StudyRecord.source.shotId")

    signals_viewed = require_list(record["signalsViewed"], "StudyRecord.signalsViewed")
    if len(signals_viewed) == 0:
        raise ValueError("StudyRecord.signalsViewed must include at least one signal.")
    require_list(record["observations"], "StudyRecord.observations")
    require_list(record["limitations"], "StudyRecord.limitations")
    return record


def validate_study_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("kind") == "openplazma.study_record":
        return _validate_notebook_record(record)

    require_keys(record, ["schemaVersion", "context", "shot", "signals"], "StudyRecord")
    if record["schemaVersion"] != "0.1.0":
        raise ValueError("StudyRecord.schemaVersion must be 0.1.0.")

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
