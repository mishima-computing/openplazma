from __future__ import annotations

from typing import Any

from ._json import load_json
from ._validation import require_keys, require_list, require_mapping, require_string


def validate_experiment_context(context: dict[str, Any]) -> dict[str, Any]:
    require_keys(context, ["kind", "version", "studyId", "createdAt", "shotRef", "signals"], "ExperimentContext")
    if context["kind"] != "openplazma.experiment_context":
        raise ValueError("ExperimentContext kind must be 'openplazma.experiment_context'.")

    require_string(context["version"], "ExperimentContext.version")
    require_string(context["studyId"], "ExperimentContext.studyId")
    require_string(context["createdAt"], "ExperimentContext.createdAt")

    shot_ref = require_mapping(context["shotRef"], "ExperimentContext.shotRef")
    require_keys(shot_ref, ["provider", "shotId"], "ExperimentContext.shotRef")
    if shot_ref["provider"] != "STATIC_FIXTURE":
        raise ValueError("ExperimentContext.shotRef.provider must be STATIC_FIXTURE for M2.")
    require_string(shot_ref["shotId"], "ExperimentContext.shotRef.shotId")

    signals = require_list(context["signals"], "ExperimentContext.signals")
    if len(signals) == 0:
        raise ValueError("ExperimentContext.signals must include at least one signal.")

    for index, signal_ref in enumerate(signals):
        signal = require_mapping(signal_ref, f"ExperimentContext.signals[{index}]")
        require_keys(signal, ["signalId"], f"ExperimentContext.signals[{index}]")
        require_string(signal["signalId"], f"ExperimentContext.signals[{index}].signalId")

    return context


def load_experiment_context(path: str) -> dict[str, Any]:
    return validate_experiment_context(load_json(path))
