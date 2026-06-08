"""Validators for the MHD mode-analysis contracts.

Mirrors packages/core/src/mhd.ts and packages/schema/src/mhd.schema.ts so the
Python SDK stays in lock-step with the TypeScript domain types. Read-only:
nothing here drives a facility or implies live telemetry.
"""

from __future__ import annotations

from typing import Any

from ._validation import require_keys, require_list, require_mapping, require_string

_PROVENANCE_KINDS = {"fixture", "measured", "derived", "synthetic"}
_PHENOMENA = {
    "mode_onset",
    "rotation_slowdown",
    "mode_locking",
    "current_quench",
    "disruption",
    "elm_crash",
    "sawtooth_crash",
    "ntm_onset",
    "ntm_saturation",
    "radiative_collapse",
    "density_limit",
}
_VERDICTS = {"support", "contradict", "inconclusive"}


def _require_version(value: dict[str, Any], name: str) -> None:
    if value.get("version") != "0.1.0":
        raise ValueError(f"{name}.version must be 0.1.0.")


def _require_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number.")
    return float(value)


def _validate_geometry(geometry: dict[str, Any], name: str) -> None:
    require_keys(geometry, ["poloidalAngleRad", "toroidalAngleRad", "majorRadiusM"], name)
    _require_number(geometry["poloidalAngleRad"], f"{name}.poloidalAngleRad")
    _require_number(geometry["toroidalAngleRad"], f"{name}.toroidalAngleRad")
    _require_number(geometry["majorRadiusM"], f"{name}.majorRadiusM")


def _validate_channel(channel: dict[str, Any], name: str) -> None:
    require_keys(channel, ["kind", "version", "channelId", "label", "signalId", "diagnosticKind", "geometry"], name)
    if channel["kind"] != "openplazma.diagnostic_channel":
        raise ValueError(f"{name}.kind must be openplazma.diagnostic_channel.")
    _require_version(channel, name)
    require_string(channel["channelId"], f"{name}.channelId")
    require_string(channel["signalId"], f"{name}.signalId")
    if channel["diagnosticKind"] not in {"magnetic_probe", "flux_loop"}:
        raise ValueError(f"{name}.diagnosticKind must be magnetic_probe or flux_loop.")
    _validate_geometry(require_mapping(channel["geometry"], f"{name}.geometry"), f"{name}.geometry")


def _validate_array(array: dict[str, Any], name: str) -> None:
    require_keys(array, ["kind", "version", "arrayId", "label", "arrayKind", "channels"], name)
    if array["kind"] != "openplazma.diagnostic_array":
        raise ValueError(f"{name}.kind must be openplazma.diagnostic_array.")
    _require_version(array, name)
    require_string(array["arrayId"], f"{name}.arrayId")
    if array["arrayKind"] not in {"mirnov_toroidal", "mirnov_poloidal"}:
        raise ValueError(f"{name}.arrayKind must be mirnov_toroidal or mirnov_poloidal.")
    channels = require_list(array["channels"], f"{name}.channels")
    if len(channels) == 0:
        raise ValueError(f"{name}.channels must include at least one channel.")
    for index, channel in enumerate(channels):
        _validate_channel(require_mapping(channel, f"{name}.channels[{index}]"), f"{name}.channels[{index}]")


def _validate_event(event: dict[str, Any], name: str) -> None:
    require_keys(event, ["kind", "version", "eventId", "phenomenon", "label", "timeRange"], name)
    if event["kind"] != "openplazma.phenomenon_event":
        raise ValueError(f"{name}.kind must be openplazma.phenomenon_event.")
    _require_version(event, name)
    if event["phenomenon"] not in _PHENOMENA:
        raise ValueError(f"{name}.phenomenon must be one of {sorted(_PHENOMENA)}.")
    _validate_time_range(event["timeRange"], f"{name}.timeRange")


def _validate_time_range(value: Any, name: str) -> None:
    pair = require_list(value, name)
    if len(pair) != 2:
        raise ValueError(f"{name} must be a [start, end] pair.")
    _require_number(pair[0], f"{name}[0]")
    _require_number(pair[1], f"{name}[1]")


def _validate_observation_model(model: dict[str, Any], name: str) -> None:
    require_keys(
        model,
        ["kind", "version", "modelId", "label", "modelType", "targetArrayId", "hypothesis", "producedSignalIds", "assumptions", "limitations"],
        name,
    )
    if model["kind"] != "openplazma.observation_model":
        raise ValueError(f"{name}.kind must be openplazma.observation_model.")
    _require_version(model, name)
    require_string(model["modelId"], f"{name}.modelId")
    if model["modelType"] != "analytic_tearing_mode":
        raise ValueError(f"{name}.modelType must be analytic_tearing_mode.")
    require_string(model["targetArrayId"], f"{name}.targetArrayId")
    hypothesis = require_mapping(model["hypothesis"], f"{name}.hypothesis")
    require_keys(hypothesis, ["poloidalModeNumber", "toroidalModeNumber", "amplitude", "rotationFreqHz", "phaseRad", "timeRange"], f"{name}.hypothesis")
    require_list(model["producedSignalIds"], f"{name}.producedSignalIds")


def _validate_inference(inference: dict[str, Any], name: str) -> None:
    require_keys(
        inference,
        ["kind", "version", "inferenceId", "label", "method", "sourceArrayId", "modeEstimate", "rotationTrack", "lockingDetected", "assumptions", "limitations"],
        name,
    )
    if inference["kind"] != "openplazma.inference":
        raise ValueError(f"{name}.kind must be openplazma.inference.")
    _require_version(inference, name)
    require_string(inference["inferenceId"], f"{name}.inferenceId")
    if inference["method"] != "magnetic_mode_phase_fit":
        raise ValueError(f"{name}.method must be magnetic_mode_phase_fit.")
    require_string(inference["sourceArrayId"], f"{name}.sourceArrayId")
    if not isinstance(inference["lockingDetected"], bool):
        raise ValueError(f"{name}.lockingDetected must be a boolean.")
    require_list(inference["rotationTrack"], f"{name}.rotationTrack")


def _validate_elm(elm: dict[str, Any], name: str) -> None:
    require_keys(
        elm,
        ["kind", "version", "analysisId", "label", "sourceSignalId", "crashes", "elmFrequencyHz", "regularity", "classification", "assumptions", "limitations"],
        name,
    )
    if elm["kind"] != "openplazma.elm_analysis":
        raise ValueError(f"{name}.kind must be openplazma.elm_analysis.")
    _require_version(elm, name)
    require_string(elm["analysisId"], f"{name}.analysisId")
    require_string(elm["sourceSignalId"], f"{name}.sourceSignalId")
    if elm["classification"] not in {"type_I", "type_III", "unknown"}:
        raise ValueError(f"{name}.classification must be type_I, type_III, or unknown.")
    _require_number(elm["elmFrequencyHz"], f"{name}.elmFrequencyHz")
    regularity = _require_number(elm["regularity"], f"{name}.regularity")
    if not 0 <= regularity <= 1:
        raise ValueError(f"{name}.regularity must be between 0 and 1.")
    require_list(elm["crashes"], f"{name}.crashes")


def _validate_claim(claim: dict[str, Any], name: str, model_ids: set[str], inference_ids: set[str], elm_ids: set[str], array_ids: set[str], event_ids: set[str]) -> None:
    require_keys(claim, ["kind", "version", "claimId", "statement", "evidence"], name)
    if claim["kind"] != "openplazma.claim":
        raise ValueError(f"{name}.kind must be openplazma.claim.")
    _require_version(claim, name)
    require_string(claim["claimId"], f"{name}.claimId")
    require_string(claim["statement"], f"{name}.statement")
    model_id = claim.get("observationModelId")
    inference_id = claim.get("inferenceId")
    elm_id = claim.get("elmAnalysisId")
    claim_event_ids = claim.get("eventIds") or []
    if model_id is None and inference_id is None and elm_id is None and not claim_event_ids:
        raise ValueError(f"{name} must reference an observation model, inference, ELM analysis, or events.")
    if model_id is not None and model_id not in model_ids:
        raise ValueError(f"{name} references unknown observation model '{model_id}'.")
    if inference_id is not None and inference_id not in inference_ids:
        raise ValueError(f"{name} references unknown inference '{inference_id}'.")
    if elm_id is not None and elm_id not in elm_ids:
        raise ValueError(f"{name} references unknown ELM analysis '{elm_id}'.")
    for event_id in claim_event_ids:
        if event_id not in event_ids:
            raise ValueError(f"{name} references unknown event '{event_id}'.")
    for index, link in enumerate(require_list(claim["evidence"], f"{name}.evidence")):
        link_map = require_mapping(link, f"{name}.evidence[{index}]")
        require_keys(link_map, ["kind", "version", "verdict", "timeRange", "rationale"], f"{name}.evidence[{index}]")
        if link_map["verdict"] not in _VERDICTS:
            raise ValueError(f"{name}.evidence[{index}].verdict must be one of {sorted(_VERDICTS)}.")
        if link_map.get("arrayId") is not None and link_map["arrayId"] not in array_ids:
            raise ValueError(f"{name}.evidence[{index}] references unknown array '{link_map['arrayId']}'.")


def validate_mhd_analysis_bundle(bundle: dict[str, Any], signal_ids: set[str] | None = None) -> dict[str, Any]:
    require_keys(
        bundle,
        ["kind", "version", "arrays", "events", "observationModels", "inferences", "claims", "provenanceKind"],
        "MhdAnalysisBundle",
    )
    if bundle["kind"] != "openplazma.mhd_analysis_bundle":
        raise ValueError("MhdAnalysisBundle.kind must be openplazma.mhd_analysis_bundle.")
    _require_version(bundle, "MhdAnalysisBundle")
    if bundle["provenanceKind"] not in _PROVENANCE_KINDS:
        raise ValueError("MhdAnalysisBundle.provenanceKind must be a valid provenance kind.")

    arrays = require_list(bundle["arrays"], "MhdAnalysisBundle.arrays")
    events = require_list(bundle["events"], "MhdAnalysisBundle.events")
    models = require_list(bundle["observationModels"], "MhdAnalysisBundle.observationModels")
    inferences = require_list(bundle["inferences"], "MhdAnalysisBundle.inferences")
    claims = require_list(bundle["claims"], "MhdAnalysisBundle.claims")
    elms = bundle.get("elmAnalyses")
    if elms is not None:
        elms = require_list(elms, "MhdAnalysisBundle.elmAnalyses")

    if len(arrays) == 0 and len(models) == 0 and len(inferences) == 0 and len(events) == 0 and len(claims) == 0 and not elms:
        raise ValueError("MhdAnalysisBundle must contain at least one array, model, inference, ELM analysis, event, or claim.")

    for index, array in enumerate(arrays):
        _validate_array(require_mapping(array, f"MhdAnalysisBundle.arrays[{index}]"), f"MhdAnalysisBundle.arrays[{index}]")
    for index, event in enumerate(events):
        _validate_event(require_mapping(event, f"MhdAnalysisBundle.events[{index}]"), f"MhdAnalysisBundle.events[{index}]")
    for index, model in enumerate(models):
        _validate_observation_model(require_mapping(model, f"MhdAnalysisBundle.observationModels[{index}]"), f"MhdAnalysisBundle.observationModels[{index}]")
    for index, inference in enumerate(inferences):
        _validate_inference(require_mapping(inference, f"MhdAnalysisBundle.inferences[{index}]"), f"MhdAnalysisBundle.inferences[{index}]")
    for index, elm in enumerate(elms or []):
        _validate_elm(require_mapping(elm, f"MhdAnalysisBundle.elmAnalyses[{index}]"), f"MhdAnalysisBundle.elmAnalyses[{index}]")

    array_ids = {array["arrayId"] for array in arrays}
    model_ids = {model["modelId"] for model in models}
    inference_ids = {inference["inferenceId"] for inference in inferences}
    elm_ids = {elm["analysisId"] for elm in (elms or [])}
    event_ids = {event["eventId"] for event in events}

    for model in models:
        if model["targetArrayId"] not in array_ids:
            raise ValueError(f"observation model '{model['modelId']}' targets unknown array '{model['targetArrayId']}'.")
    for inference in inferences:
        if inference["sourceArrayId"] not in array_ids:
            raise ValueError(f"inference '{inference['inferenceId']}' references unknown array '{inference['sourceArrayId']}'.")
    for index, claim in enumerate(claims):
        _validate_claim(require_mapping(claim, f"MhdAnalysisBundle.claims[{index}]"), f"MhdAnalysisBundle.claims[{index}]", model_ids, inference_ids, elm_ids, array_ids, event_ids)

    if signal_ids is not None:
        for array in arrays:
            for channel in array["channels"]:
                if channel["signalId"] not in signal_ids:
                    raise ValueError(f"diagnostic channel '{channel['channelId']}' references missing signal '{channel['signalId']}'.")
        for model in models:
            for produced in model["producedSignalIds"]:
                if produced not in signal_ids:
                    raise ValueError(f"observation model '{model['modelId']}' produced signal '{produced}' is not in signals.")
        for elm in elms or []:
            if elm["sourceSignalId"] not in signal_ids:
                raise ValueError(f"ELM analysis '{elm['analysisId']}' references missing signal '{elm['sourceSignalId']}'.")

    return bundle
