from __future__ import annotations

from typing import Any

from ._json import load_json
from ._validation import require_finite_number, require_iso_datetime, require_keys, require_list, require_mapping, require_string
from .sources import validate_data_provider, validate_source_ref


def _validate_time_range(value: Any, name: str) -> None:
    items = require_list(value, name)
    if len(items) != 2:
        raise ValueError(f"{name} must be a [start, end] pair.")
    require_finite_number(items[0], f"{name}[0]")
    require_finite_number(items[1], f"{name}[1]")


def _validate_signal_ref(signal_ref: dict[str, Any], name: str) -> None:
    require_keys(signal_ref, ["signalId"], name)
    require_string(signal_ref["signalId"], f"{name}.signalId")
    for field in ["label", "quantity", "unit"]:
        if signal_ref.get(field) is not None:
            require_string(signal_ref[field], f"{name}.{field}")


def _validate_observation(observation: dict[str, Any], name: str) -> None:
    require_keys(observation, ["text"], name)
    require_string(observation["text"], f"{name}.text")
    if observation.get("signalId") is not None:
        require_string(observation["signalId"], f"{name}.signalId")
    if observation.get("timeRange") is not None:
        _validate_time_range(observation["timeRange"], f"{name}.timeRange")


def _validate_string_list(value: Any, name: str, *, min_items: int = 0) -> list[Any]:
    items = require_list(value, name)
    if len(items) < min_items:
        raise ValueError(f"{name} must include at least {min_items} item(s).")
    for index, item in enumerate(items):
        require_string(item, f"{name}[{index}]")
    return items


def validate_experiment_context(context: dict[str, Any]) -> dict[str, Any]:
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
        "ExperimentContext",
    )
    if context["kind"] != "openplazma.experiment_context":
        raise ValueError("ExperimentContext kind must be 'openplazma.experiment_context'.")
    if context["version"] != "0.1.0":
        raise ValueError("ExperimentContext.version must be 0.1.0.")

    require_string(context["contextId"], "ExperimentContext.contextId")
    require_string(context["projectId"], "ExperimentContext.projectId")
    require_string(context["datasetId"], "ExperimentContext.datasetId")
    require_string(context["description"], "ExperimentContext.description")
    require_iso_datetime(context["createdAt"], "ExperimentContext.createdAt")

    target = require_mapping(context["target"], "ExperimentContext.target")
    require_keys(target, ["type", "id", "label"], "ExperimentContext.target")
    if target["type"] not in {"static_fixture", "local_run_store", "public_observation_dataset"}:
        raise ValueError("ExperimentContext.target.type must be static_fixture, local_run_store, or public_observation_dataset.")
    require_string(target["id"], "ExperimentContext.target.id")
    require_string(target["label"], "ExperimentContext.target.label")

    source = require_mapping(context["source"], "ExperimentContext.source")
    validate_source_ref(source, "ExperimentContext.source")

    if source["provider"] == "STATIC_FIXTURE":
        if context["safetyClassification"] != "public-educational-fixture":
            raise ValueError("ExperimentContext.safetyClassification must be public-educational-fixture for STATIC_FIXTURE.")
        if target["type"] != "static_fixture":
            raise ValueError("ExperimentContext.target.type must be static_fixture for STATIC_FIXTURE.")
    elif source["provider"] == "LOCAL_SIGNAL_FILE":
        if context["safetyClassification"] != "read-only-local-signal":
            raise ValueError("ExperimentContext.safetyClassification must be read-only-local-signal for LOCAL_SIGNAL_FILE.")
        if target["type"] != "local_run_store":
            raise ValueError("ExperimentContext.target.type must be local_run_store for LOCAL_SIGNAL_FILE.")
    else:
        if context["safetyClassification"] != "public-web-observation":
            raise ValueError("ExperimentContext.safetyClassification must be public-web-observation for NOAA_SWPC.")
        if target["type"] != "public_observation_dataset":
            raise ValueError("ExperimentContext.target.type must be public_observation_dataset for NOAA_SWPC.")

    capabilities = require_mapping(context["capabilities"], "ExperimentContext.capabilities")
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
        "ExperimentContext.capabilities",
    )
    if capabilities["controlFacility"] is not False:
        raise ValueError("ExperimentContext.capabilities.controlFacility must be false.")
    for field in ["readData", "writeArtifacts"]:
        if capabilities[field] is not True:
            raise ValueError(f"ExperimentContext.capabilities.{field} must be true.")
    for field in ["runSimulation", "submitComputeJob", "readFacilityTelemetry"]:
        if capabilities[field] is not False:
            raise ValueError(f"ExperimentContext.capabilities.{field} must be false.")

    shot_ref = require_mapping(context["shotRef"], "ExperimentContext.shotRef")
    require_keys(shot_ref, ["provider", "shotId"], "ExperimentContext.shotRef")
    validate_data_provider(shot_ref["provider"], "ExperimentContext.shotRef.provider")
    if shot_ref["provider"] != source["provider"]:
        raise ValueError("ExperimentContext.shotRef.provider must match ExperimentContext.source.provider.")
    require_string(shot_ref["shotId"], "ExperimentContext.shotRef.shotId")

    signals = require_list(context["signals"], "ExperimentContext.signals")
    if len(signals) == 0:
        raise ValueError("ExperimentContext.signals must include at least one signal.")

    for index, signal_ref in enumerate(signals):
        signal = require_mapping(signal_ref, f"ExperimentContext.signals[{index}]")
        _validate_signal_ref(signal, f"ExperimentContext.signals[{index}]")

    if context.get("view") is not None:
        view = require_mapping(context["view"], "ExperimentContext.view")
        if view.get("timeRange") is not None:
            _validate_time_range(view["timeRange"], "ExperimentContext.view.timeRange")

    observations = require_list(context["observations"], "ExperimentContext.observations")
    for index, observation_ref in enumerate(observations):
        observation = require_mapping(observation_ref, f"ExperimentContext.observations[{index}]")
        _validate_observation(observation, f"ExperimentContext.observations[{index}]")
    _validate_string_list(context["limitations"], "ExperimentContext.limitations", min_items=1)

    return context


def load_experiment_context(path: str) -> dict[str, Any]:
    return validate_experiment_context(load_json(path))
