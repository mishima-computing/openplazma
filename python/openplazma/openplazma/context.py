from __future__ import annotations

from typing import Any

from ._json import load_json
from ._validation import require_keys, require_list, require_mapping, require_string
from .sources import validate_data_provider, validate_source_ref


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
    require_string(context["createdAt"], "ExperimentContext.createdAt")

    target = require_mapping(context["target"], "ExperimentContext.target")
    require_keys(target, ["type", "id", "label"], "ExperimentContext.target")
    if target["type"] not in {"static_fixture", "local_run_store"}:
        raise ValueError("ExperimentContext.target.type must be static_fixture or local_run_store.")
    require_string(target["id"], "ExperimentContext.target.id")
    require_string(target["label"], "ExperimentContext.target.label")

    source = require_mapping(context["source"], "ExperimentContext.source")
    validate_source_ref(source, "ExperimentContext.source")

    if source["provider"] == "STATIC_FIXTURE":
        if context["safetyClassification"] != "public-educational-fixture":
            raise ValueError("ExperimentContext.safetyClassification must be public-educational-fixture for STATIC_FIXTURE.")
        if target["type"] != "static_fixture":
            raise ValueError("ExperimentContext.target.type must be static_fixture for STATIC_FIXTURE.")
    else:
        if context["safetyClassification"] != "read-only-local-signal":
            raise ValueError("ExperimentContext.safetyClassification must be read-only-local-signal for LOCAL_SIGNAL_FILE.")
        if target["type"] != "local_run_store":
            raise ValueError("ExperimentContext.target.type must be local_run_store for LOCAL_SIGNAL_FILE.")

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
        require_keys(signal, ["signalId"], f"ExperimentContext.signals[{index}]")
        require_string(signal["signalId"], f"ExperimentContext.signals[{index}].signalId")

    require_list(context["observations"], "ExperimentContext.observations")
    limitations = require_list(context["limitations"], "ExperimentContext.limitations")
    if len(limitations) == 0:
        raise ValueError("ExperimentContext.limitations must include at least one limitation.")

    return context


def load_experiment_context(path: str) -> dict[str, Any]:
    return validate_experiment_context(load_json(path))
