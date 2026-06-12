"""Validators for the MHD mode-analysis contracts.

Mirrors packages/core/src/mhd.ts and packages/schema/src/mhd.schema.ts so the
Python SDK stays in lock-step with the TypeScript domain types. Read-only:
nothing here drives a facility or implies live telemetry.
"""

from __future__ import annotations

from typing import Any

from ._validation import require_finite_number, require_keys, require_list, require_mapping, require_string

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
_READOUT_KINDS = {
    "phase_fit",
    "frequency_track",
    "threshold_crossing",
    "event_detection",
    "elm_detection",
    "model_readout",
    "manual_annotation",
    "unknown",
}
_OBSERVABLES = {
    "magnetic_field",
    "electric_current",
    "loop_voltage",
    "radiation",
    "light_intensity",
    "stored_energy",
    "density",
    "motion",
    "unknown",
}
_READOUT_STATUSES = {"detected", "not_detected", "candidate", "inconclusive", "unknown"}


def _require_version(value: dict[str, Any], name: str) -> None:
    if value.get("version") != "0.1.0":
        raise ValueError(f"{name}.version must be 0.1.0.")


def _require_number(value: Any, name: str) -> float:
    return require_finite_number(value, name)


def _require_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer.")
    return value


def _require_string_list(value: Any, name: str) -> None:
    for index, item in enumerate(require_list(value, name)):
        require_string(item, f"{name}[{index}]")


def _validate_geometry(geometry: dict[str, Any], name: str) -> None:
    require_keys(geometry, ["poloidalAngleRad", "toroidalAngleRad", "majorRadiusM"], name)
    _require_number(geometry["poloidalAngleRad"], f"{name}.poloidalAngleRad")
    _require_number(geometry["toroidalAngleRad"], f"{name}.toroidalAngleRad")
    require_finite_number(geometry["majorRadiusM"], f"{name}.majorRadiusM", positive=True)
    if geometry.get("minorRadiusM") is not None:
        require_finite_number(geometry["minorRadiusM"], f"{name}.minorRadiusM", positive=True)


def _validate_channel(channel: dict[str, Any], name: str) -> None:
    require_keys(channel, ["kind", "version", "channelId", "label", "signalId", "diagnosticKind", "geometry"], name)
    if channel["kind"] != "openplazma.diagnostic_channel":
        raise ValueError(f"{name}.kind must be openplazma.diagnostic_channel.")
    _require_version(channel, name)
    require_string(channel["channelId"], f"{name}.channelId")
    require_string(channel["label"], f"{name}.label")
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
    require_string(array["label"], f"{name}.label")
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
    require_string(event["eventId"], f"{name}.eventId")
    if event["phenomenon"] not in _PHENOMENA:
        raise ValueError(f"{name}.phenomenon must be one of {sorted(_PHENOMENA)}.")
    require_string(event["label"], f"{name}.label")
    _validate_time_range(event["timeRange"], f"{name}.timeRange")
    if event.get("signalId") is not None:
        require_string(event["signalId"], f"{name}.signalId")
    if event.get("producedByInferenceId") is not None:
        require_string(event["producedByInferenceId"], f"{name}.producedByInferenceId")
    if event.get("evidenceReadoutIds") is not None:
        _require_string_list(event["evidenceReadoutIds"], f"{name}.evidenceReadoutIds")
    if event.get("notes") is not None:
        require_string(event["notes"], f"{name}.notes")


def _validate_time_range(value: Any, name: str) -> None:
    pair = require_list(value, name)
    if len(pair) != 2:
        raise ValueError(f"{name} must be a [start, end] pair.")
    _require_number(pair[0], f"{name}[0]")
    _require_number(pair[1], f"{name}[1]")


def _validate_observation_model(model: dict[str, Any], name: str) -> None:
    require_keys(
        model,
        [
            "kind",
            "version",
            "modelId",
            "label",
            "modelType",
            "targetArrayId",
            "hypothesis",
            "producedSignalIds",
            "assumptions",
            "limitations",
        ],
        name,
    )
    if model["kind"] != "openplazma.observation_model":
        raise ValueError(f"{name}.kind must be openplazma.observation_model.")
    _require_version(model, name)
    require_string(model["modelId"], f"{name}.modelId")
    require_string(model["label"], f"{name}.label")
    if model["modelType"] != "analytic_tearing_mode":
        raise ValueError(f"{name}.modelType must be analytic_tearing_mode.")
    require_string(model["targetArrayId"], f"{name}.targetArrayId")
    hypothesis = require_mapping(model["hypothesis"], f"{name}.hypothesis")
    require_keys(
        hypothesis,
        ["poloidalModeNumber", "toroidalModeNumber", "amplitude", "rotationFreqHz", "phaseRad", "timeRange"],
        f"{name}.hypothesis",
    )
    _require_int(hypothesis["poloidalModeNumber"], f"{name}.hypothesis.poloidalModeNumber")
    _require_int(hypothesis["toroidalModeNumber"], f"{name}.hypothesis.toroidalModeNumber")
    _require_number(hypothesis["amplitude"], f"{name}.hypothesis.amplitude")
    _require_number(hypothesis["rotationFreqHz"], f"{name}.hypothesis.rotationFreqHz")
    _require_number(hypothesis["phaseRad"], f"{name}.hypothesis.phaseRad")
    _validate_time_range(hypothesis["timeRange"], f"{name}.hypothesis.timeRange")
    _require_string_list(model["producedSignalIds"], f"{name}.producedSignalIds")
    _require_string_list(model["assumptions"], f"{name}.assumptions")
    _require_string_list(model["limitations"], f"{name}.limitations")


def _validate_inference(inference: dict[str, Any], name: str) -> None:
    require_keys(
        inference,
        [
            "kind",
            "version",
            "inferenceId",
            "label",
            "method",
            "sourceArrayId",
            "evidenceReadoutIds",
            "modeEstimate",
            "rotationTrack",
            "lockingDetected",
            "assumptions",
            "limitations",
            "alternatives",
        ],
        name,
    )
    if inference["kind"] != "openplazma.inference":
        raise ValueError(f"{name}.kind must be openplazma.inference.")
    _require_version(inference, name)
    require_string(inference["inferenceId"], f"{name}.inferenceId")
    require_string(inference["label"], f"{name}.label")
    if inference["method"] != "magnetic_mode_phase_fit":
        raise ValueError(f"{name}.method must be magnetic_mode_phase_fit.")
    require_string(inference["sourceArrayId"], f"{name}.sourceArrayId")
    _require_string_list(inference["evidenceReadoutIds"], f"{name}.evidenceReadoutIds")
    estimate = require_mapping(inference["modeEstimate"], f"{name}.modeEstimate")
    require_keys(estimate, ["toroidalModeNumber", "confidence", "method"], f"{name}.modeEstimate")
    _require_int(estimate["toroidalModeNumber"], f"{name}.modeEstimate.toroidalModeNumber")
    if estimate.get("poloidalModeNumber") is not None:
        _require_int(estimate["poloidalModeNumber"], f"{name}.modeEstimate.poloidalModeNumber")
    confidence = _require_number(estimate["confidence"], f"{name}.modeEstimate.confidence")
    if not 0 <= confidence <= 1:
        raise ValueError(f"{name}.modeEstimate.confidence must be between 0 and 1.")
    if estimate["method"] not in {"phase_fit_toroidal", "phase_fit_poloidal"}:
        raise ValueError(f"{name}.modeEstimate.method must be phase_fit_toroidal or phase_fit_poloidal.")
    if estimate.get("islandWidthM") is not None:
        require_finite_number(estimate["islandWidthM"], f"{name}.modeEstimate.islandWidthM", nonnegative=True)
    if not isinstance(inference["lockingDetected"], bool):
        raise ValueError(f"{name}.lockingDetected must be a boolean.")
    for index, point_ref in enumerate(require_list(inference["rotationTrack"], f"{name}.rotationTrack")):
        point = require_mapping(point_ref, f"{name}.rotationTrack[{index}]")
        require_keys(point, ["time", "rotationFreqHz", "amplitude"], f"{name}.rotationTrack[{index}]")
        _require_number(point["time"], f"{name}.rotationTrack[{index}].time")
        _require_number(point["rotationFreqHz"], f"{name}.rotationTrack[{index}].rotationFreqHz")
        _require_number(point["amplitude"], f"{name}.rotationTrack[{index}].amplitude")
    if inference.get("lockTimeRange") is not None:
        _validate_time_range(inference["lockTimeRange"], f"{name}.lockTimeRange")
    _require_string_list(inference["assumptions"], f"{name}.assumptions")
    _require_string_list(inference["limitations"], f"{name}.limitations")
    _require_string_list(inference["alternatives"], f"{name}.alternatives")


def _validate_readout(readout: dict[str, Any], name: str) -> None:
    require_keys(
        readout,
        [
            "kind",
            "version",
            "readoutId",
            "readoutKind",
            "observable",
            "method",
            "status",
            "assumptions",
            "limitations",
            "alternatives",
        ],
        name,
    )
    if readout["kind"] != "openplazma.mhd_observation_statement":
        raise ValueError(f"{name}.kind must be openplazma.mhd_observation_statement.")
    _require_version(readout, name)
    require_string(readout["readoutId"], f"{name}.readoutId")
    if readout["readoutKind"] not in _READOUT_KINDS:
        raise ValueError(f"{name}.readoutKind must be one of {sorted(_READOUT_KINDS)}.")
    if readout["observable"] not in _OBSERVABLES:
        raise ValueError(f"{name}.observable must be one of {sorted(_OBSERVABLES)}.")
    for field in ["signalId", "arrayId", "observationModelId", "inferenceId", "eventId", "unit"]:
        if readout.get(field) is not None:
            require_string(readout[field], f"{name}.{field}")
    require_string(readout["method"], f"{name}.method")
    if readout["status"] not in _READOUT_STATUSES:
        raise ValueError(f"{name}.status must be one of {sorted(_READOUT_STATUSES)}.")
    if readout.get("timeRange") is not None:
        _validate_time_range(readout["timeRange"], f"{name}.timeRange")
    if readout.get("value") is not None:
        _require_number(readout["value"], f"{name}.value")
    _require_string_list(readout["assumptions"], f"{name}.assumptions")
    _require_string_list(readout["limitations"], f"{name}.limitations")
    _require_string_list(readout["alternatives"], f"{name}.alternatives")


def _validate_elm(elm: dict[str, Any], name: str) -> None:
    require_keys(
        elm,
        [
            "kind",
            "version",
            "analysisId",
            "label",
            "sourceSignalId",
            "crashes",
            "elmFrequencyHz",
            "regularity",
            "classification",
            "assumptions",
            "limitations",
        ],
        name,
    )
    if elm["kind"] != "openplazma.elm_analysis":
        raise ValueError(f"{name}.kind must be openplazma.elm_analysis.")
    _require_version(elm, name)
    require_string(elm["analysisId"], f"{name}.analysisId")
    require_string(elm["label"], f"{name}.label")
    require_string(elm["sourceSignalId"], f"{name}.sourceSignalId")
    if elm["classification"] not in {"type_I", "type_III", "unknown"}:
        raise ValueError(f"{name}.classification must be type_I, type_III, or unknown.")
    require_finite_number(elm["elmFrequencyHz"], f"{name}.elmFrequencyHz", nonnegative=True)
    regularity = _require_number(elm["regularity"], f"{name}.regularity")
    if not 0 <= regularity <= 1:
        raise ValueError(f"{name}.regularity must be between 0 and 1.")
    for index, crash_ref in enumerate(require_list(elm["crashes"], f"{name}.crashes")):
        crash = require_mapping(crash_ref, f"{name}.crashes[{index}]")
        require_keys(crash, ["time", "amplitude"], f"{name}.crashes[{index}]")
        _require_number(crash["time"], f"{name}.crashes[{index}].time")
        _require_number(crash["amplitude"], f"{name}.crashes[{index}].amplitude")
    _require_string_list(elm["assumptions"], f"{name}.assumptions")
    _require_string_list(elm["limitations"], f"{name}.limitations")


def _validate_claim(
    claim: dict[str, Any],
    name: str,
    model_ids: set[str],
    inference_ids: set[str],
    elm_ids: set[str],
    array_ids: set[str],
    event_ids: set[str],
    readout_ids: set[str],
) -> None:
    require_keys(claim, ["kind", "version", "claimId", "statement", "evidence"], name)
    if claim["kind"] != "openplazma.claim":
        raise ValueError(f"{name}.kind must be openplazma.claim.")
    _require_version(claim, name)
    require_string(claim["claimId"], f"{name}.claimId")
    require_string(claim["statement"], f"{name}.statement")
    for field in ["observationModelId", "inferenceId", "elmAnalysisId"]:
        if claim.get(field) is not None:
            require_string(claim[field], f"{name}.{field}")
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
        require_string(event_id, f"{name}.eventIds[]")
        if event_id not in event_ids:
            raise ValueError(f"{name} references unknown event '{event_id}'.")
    evidence = require_list(claim["evidence"], f"{name}.evidence")
    if len(evidence) == 0:
        raise ValueError(f"{name} requires evidence.")
    for index, link in enumerate(evidence):
        link_map = require_mapping(link, f"{name}.evidence[{index}]")
        require_keys(
            link_map,
            [
                "kind",
                "version",
                "verdict",
                "method",
                "timeRange",
                "rationale",
                "assumptions",
                "limitations",
                "alternatives",
            ],
            f"{name}.evidence[{index}]",
        )
        if link_map["kind"] != "openplazma.evidence_link":
            raise ValueError(f"{name}.evidence[{index}].kind must be openplazma.evidence_link.")
        _require_version(link_map, f"{name}.evidence[{index}]")
        if link_map["verdict"] not in _VERDICTS:
            raise ValueError(f"{name}.evidence[{index}].verdict must be one of {sorted(_VERDICTS)}.")
        if link_map.get("signalId") is not None:
            require_string(link_map["signalId"], f"{name}.evidence[{index}].signalId")
        if link_map.get("arrayId") is not None and link_map["arrayId"] not in array_ids:
            raise ValueError(f"{name}.evidence[{index}] references unknown array '{link_map['arrayId']}'.")
        if link_map.get("readoutId") is not None and link_map["readoutId"] not in readout_ids:
            raise ValueError(f"{name}.evidence[{index}] references unknown mediated readout '{link_map['readoutId']}'.")
        if link_map.get("inferenceId") is not None and link_map["inferenceId"] not in inference_ids:
            raise ValueError(f"{name}.evidence[{index}] references unknown inference '{link_map['inferenceId']}'.")
        if link_map.get("eventId") is not None and link_map["eventId"] not in event_ids:
            raise ValueError(f"{name}.evidence[{index}] references unknown event '{link_map['eventId']}'.")
        has_mediated_reference = any(link_map.get(field) is not None for field in ["readoutId", "inferenceId"])
        if link_map.get("eventId") is not None and not has_mediated_reference:
            raise ValueError(f"{name} cannot use bare event evidence.")
        if not has_mediated_reference and link_map.get("eventId") is None:
            raise ValueError(f"{name}.evidence[{index}] must reference a mediated readout or inference.")
        require_string(link_map["method"], f"{name}.evidence[{index}].method")
        _validate_time_range(link_map["timeRange"], f"{name}.evidence[{index}].timeRange")
        require_string(link_map["rationale"], f"{name}.evidence[{index}].rationale")
        _require_string_list(link_map["assumptions"], f"{name}.evidence[{index}].assumptions")
        _require_string_list(link_map["limitations"], f"{name}.evidence[{index}].limitations")
        _require_string_list(link_map["alternatives"], f"{name}.evidence[{index}].alternatives")


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
    readouts = bundle.get("readouts")
    if readouts is not None:
        readouts = require_list(readouts, "MhdAnalysisBundle.readouts")
    claims = require_list(bundle["claims"], "MhdAnalysisBundle.claims")
    elms = bundle.get("elmAnalyses")
    if elms is not None:
        elms = require_list(elms, "MhdAnalysisBundle.elmAnalyses")

    if (
        len(arrays) == 0
        and len(models) == 0
        and len(inferences) == 0
        and len(events) == 0
        and len(claims) == 0
        and not readouts
        and not elms
    ):
        raise ValueError("MhdAnalysisBundle must contain at least one array, model, inference, ELM analysis, event, or claim.")

    for index, array in enumerate(arrays):
        _validate_array(require_mapping(array, f"MhdAnalysisBundle.arrays[{index}]"), f"MhdAnalysisBundle.arrays[{index}]")
    for index, event in enumerate(events):
        _validate_event(require_mapping(event, f"MhdAnalysisBundle.events[{index}]"), f"MhdAnalysisBundle.events[{index}]")
    for index, model in enumerate(models):
        _validate_observation_model(
            require_mapping(model, f"MhdAnalysisBundle.observationModels[{index}]"),
            f"MhdAnalysisBundle.observationModels[{index}]",
        )
    for index, inference in enumerate(inferences):
        _validate_inference(require_mapping(inference, f"MhdAnalysisBundle.inferences[{index}]"), f"MhdAnalysisBundle.inferences[{index}]")
    for index, readout in enumerate(readouts or []):
        _validate_readout(require_mapping(readout, f"MhdAnalysisBundle.readouts[{index}]"), f"MhdAnalysisBundle.readouts[{index}]")
    for index, elm in enumerate(elms or []):
        _validate_elm(require_mapping(elm, f"MhdAnalysisBundle.elmAnalyses[{index}]"), f"MhdAnalysisBundle.elmAnalyses[{index}]")

    array_ids = {array["arrayId"] for array in arrays}
    model_ids = {model["modelId"] for model in models}
    inference_ids = {inference["inferenceId"] for inference in inferences}
    elm_ids = {elm["analysisId"] for elm in (elms or [])}
    event_ids = {event["eventId"] for event in events}
    readout_ids: set[str] = set()
    for readout in readouts or []:
        if readout["readoutId"] in readout_ids:
            raise ValueError(f"duplicate mediated MHD readout id '{readout['readoutId']}'.")
        readout_ids.add(readout["readoutId"])
        if readout.get("arrayId") is not None and readout["arrayId"] not in array_ids:
            raise ValueError(f"mediated MHD readout '{readout['readoutId']}' references unknown array '{readout['arrayId']}'.")
        if readout.get("observationModelId") is not None and readout["observationModelId"] not in model_ids:
            raise ValueError(f"mediated MHD readout '{readout['readoutId']}' references unknown observation model '{readout['observationModelId']}'.")
        if readout.get("inferenceId") is not None and readout["inferenceId"] not in inference_ids:
            raise ValueError(f"mediated MHD readout '{readout['readoutId']}' references unknown inference '{readout['inferenceId']}'.")
        if readout.get("eventId") is not None and readout["eventId"] not in event_ids:
            raise ValueError(f"mediated MHD readout '{readout['readoutId']}' references unknown event '{readout['eventId']}'.")

    for model in models:
        if model["targetArrayId"] not in array_ids:
            raise ValueError(f"observation model '{model['modelId']}' targets unknown array '{model['targetArrayId']}'.")
    for inference in inferences:
        if inference["sourceArrayId"] not in array_ids:
            raise ValueError(f"inference '{inference['inferenceId']}' references unknown array '{inference['sourceArrayId']}'.")
        if len(inference["evidenceReadoutIds"]) == 0:
            raise ValueError(f"inference '{inference['inferenceId']}' requires mediated readout evidence.")
        for readout_id in inference["evidenceReadoutIds"]:
            if readout_id not in readout_ids:
                raise ValueError(f"inference '{inference['inferenceId']}' references unknown mediated readout '{readout_id}'.")
    for event in events:
        produced = event.get("producedByInferenceId")
        if produced is not None and produced not in inference_ids:
            raise ValueError(f"phenomenon event '{event['eventId']}' references unknown inference '{produced}'.")
        for readout_id in event.get("evidenceReadoutIds") or []:
            if readout_id not in readout_ids:
                raise ValueError(f"phenomenon event '{event['eventId']}' references unknown mediated readout '{readout_id}'.")
        if produced is None and len(event.get("evidenceReadoutIds") or []) == 0:
            raise ValueError(f"phenomenon event '{event['eventId']}' must be produced by inference or cite mediated readout evidence.")
    for index, claim in enumerate(claims):
        _validate_claim(
            require_mapping(claim, f"MhdAnalysisBundle.claims[{index}]"),
            f"MhdAnalysisBundle.claims[{index}]",
            model_ids,
            inference_ids,
            elm_ids,
            array_ids,
            event_ids,
            readout_ids,
        )

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
        for readout in readouts or []:
            if readout.get("signalId") is not None and readout["signalId"] not in signal_ids:
                raise ValueError(f"mediated MHD readout '{readout['readoutId']}' references missing signal '{readout['signalId']}'.")
        for claim in claims:
            for link in claim["evidence"]:
                if link.get("signalId") is not None and link["signalId"] not in signal_ids:
                    raise ValueError(f"claim '{claim['claimId']}' evidence references missing signal '{link['signalId']}'.")

    return bundle
