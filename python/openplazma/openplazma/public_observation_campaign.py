from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Sequence

from ._validation import require_list, require_mapping, require_string
from .investigations import (
    assess_investigation_session,
    build_investigation_package,
    create_investigation_session,
    create_investigation_session_report,
    record_investigation_report,
    log_investigation_session,
)
from .observatory import export_observatory_html
from .public_data import load_public_observation_snapshot
from .runstore import Run, start_run
from .signals import build_signal_channel_index, compute_signal_spectrum, summarize_signal_channel, validate_signal_series

VERSION = "0.1.0"
DEFAULT_PUBLIC_OBSERVATION_SIGNAL_IDS = (
    "solar-wind-proton-density",
    "imf-bz-gsm",
    "goes-xray-long-flux",
)
PRODUCT_REQUIRED_OBSERVABLES = ("neutron_flux", "gamma_ray", "temperature", "density")


def _signal_ref(signal: dict[str, Any]) -> dict[str, str]:
    return {
        "signalId": signal["signalId"],
        "label": signal["label"],
        "quantity": signal["quantity"],
        "unit": signal["unit"],
    }


def _selected_signals(snapshot: dict[str, Any], signal_ids: Sequence[str] | None) -> list[dict[str, Any]]:
    signals = [validate_signal_series(signal) for signal in require_list(snapshot["signals"], "PublicObservationSnapshot.signals")]
    by_id = {signal["signalId"]: signal for signal in signals}
    selected_ids = list(signal_ids or [signal_id for signal_id in DEFAULT_PUBLIC_OBSERVATION_SIGNAL_IDS if signal_id in by_id])
    if not selected_ids:
        selected_ids = [signal["signalId"] for signal in signals[:3]]
    if not selected_ids:
        raise ValueError("Public observation campaign requires at least one selected signal.")

    selected: list[dict[str, Any]] = []
    for index, signal_id in enumerate(selected_ids):
        selected_signal_id = require_string(signal_id, f"signal_ids[{index}]")
        if selected_signal_id not in by_id:
            raise ValueError(f"Signal '{selected_signal_id}' was not found in the public observation snapshot.")
        selected.append(by_id[selected_signal_id])
    return selected


def _dedupe(items: Sequence[str]) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            selected.append(item)
            seen.add(item)
    return selected


def _signal_semantics(signal: dict[str, Any]) -> dict[str, str]:
    signal_id = signal["signalId"]
    quantity = signal["quantity"]
    label = f"{signal_id} {quantity}".lower()
    if "xray" in label or "x-ray" in label:
        return {
            "observable": "xray",
            "instrumentKind": "xray_detector",
            "frequencyDomain": "intensity_modulation",
        }
    if "magnetic" in label or signal_id.startswith("imf-"):
        return {
            "observable": "magnetic_field",
            "instrumentKind": "magnetic_probe",
            "frequencyDomain": "magnetic_variation",
        }
    if "temperature" in label:
        return {
            "observable": "temperature",
            "instrumentKind": "particle_detector",
            "frequencyDomain": "unknown",
        }
    if "density" in label:
        return {
            "observable": "density",
            "instrumentKind": "particle_detector",
            "frequencyDomain": "unknown",
        }
    if "speed" in label or "bulk" in label:
        return {
            "observable": "motion",
            "instrumentKind": "particle_detector",
            "frequencyDomain": "motion_modulation",
        }
    return {
        "observable": "unknown",
        "instrumentKind": "unknown",
        "frequencyDomain": "unknown",
    }


def _window_summary(signal: dict[str, Any], time_window: Sequence[float] | None) -> dict[str, Any]:
    return summarize_signal_channel(signal, time_window=time_window)


def _spectrum_payload(
    signal: dict[str, Any],
    *,
    time_window: Sequence[float] | None,
    max_frequency_hz: float | None,
) -> dict[str, Any]:
    semantics = _signal_semantics(signal)
    try:
        spectrum = compute_signal_spectrum(
            signal,
            time_window=time_window,
            spectrum_id=f"public-spectrum-{signal['signalId']}",
            max_frequency_hz=max_frequency_hz,
            include_dc=False,
        )
    except ValueError as error:
        summary = _window_summary(signal, time_window)
        return {
            "kind": "openplazma.public_observation_spectrum",
            "version": VERSION,
            "spectrumId": f"public-spectrum-{signal['signalId']}",
            "sourceSignalId": signal["signalId"],
            "status": "not_computed",
            "signal": _signal_ref(signal),
            "timeRange": summary["timeRange"],
            "spectrum": {
                "spectrumKind": "frequency_metadata",
                "domain": semantics["frequencyDomain"],
                "frequencyUnit": "Hz",
                "frequenciesHz": [],
                "amplitudes": [],
            },
            "assumptions": ["The signal is part of a frozen public observation snapshot."],
            "limitations": [
                str(error),
                "Frequency metadata is recorded, but no DFT spectrum was produced for this signal window.",
                "No calibrated fusion product or fusion-condition interpretation is attached.",
            ],
        }

    frequencies = [bin_ref["frequencyHz"] for bin_ref in spectrum["bins"]]
    amplitudes = [bin_ref["amplitude"] for bin_ref in spectrum["bins"]]
    dominant = max(spectrum["bins"], key=lambda bin_ref: bin_ref["amplitude"]) if spectrum["bins"] else None
    return {
        "kind": "openplazma.public_observation_spectrum",
        "version": VERSION,
        "spectrumId": spectrum["spectrumId"],
        "sourceSignalId": signal["signalId"],
        "status": "computed",
        "signal": _signal_ref(signal),
        "timeRange": spectrum["timeRange"],
        "spectrum": {
            "spectrumKind": "signal_amplitude_spectrum",
            "domain": semantics["frequencyDomain"],
            "frequencyUnit": spectrum["frequencyUnit"],
            "amplitudeUnit": spectrum["amplitudeUnit"],
            "frequenciesHz": frequencies,
            "amplitudes": amplitudes,
        },
        "dominantPeak": dominant,
        "signalSpectrum": spectrum,
        "assumptions": [
            *spectrum["assumptions"],
            "The signal is part of a frozen public observation snapshot.",
        ],
        "limitations": [
            *spectrum["limitations"],
            "No calibrated fusion product or fusion-condition interpretation is attached.",
        ],
    }


def _frequency_analysis(signal: dict[str, Any], spectrum_payload: dict[str, Any]) -> dict[str, Any]:
    semantics = _signal_semantics(signal)
    spectrum = require_mapping(spectrum_payload["spectrum"], "PublicObservationSpectrum.spectrum")
    frequencies = spectrum.get("frequenciesHz") if isinstance(spectrum.get("frequenciesHz"), list) else []
    dominant = spectrum_payload.get("dominantPeak") if isinstance(spectrum_payload.get("dominantPeak"), dict) else None
    peaks = []
    if dominant is not None and dominant.get("frequencyHz") is not None:
        peaks.append(
            {
                "peakId": f"{signal['signalId']}-dominant-frequency",
                "frequencyHz": dominant["frequencyHz"],
                "amplitude": dominant.get("amplitude"),
                "phaseRadians": dominant.get("phaseRad"),
                "interpretation": "Dominant non-DC modulation in the selected public signal window.",
                "limitations": [
                    "Dominant modulation is descriptive metadata, not calibrated source identification.",
                    "No fusion product or condition evidence is inferred from this peak.",
                ],
            }
        )

    band: dict[str, Any] = {
        "bandId": f"{signal['signalId']}-signal-window-band",
        "domain": semantics["frequencyDomain"],
        "label": f"{signal['label']} selected signal window",
        "quantity": signal["quantity"],
        "unit": signal["unit"],
        "description": "Frequency coverage metadata for the selected public signal window.",
        "limitations": [
            "The band describes sampled public data-product variability only.",
            "The band is not a calibrated fusion-condition diagnostic.",
        ],
    }
    if frequencies:
        band["lowerFrequencyHz"] = min(frequencies)
        band["upperFrequencyHz"] = max(frequencies)
        if dominant is not None and dominant.get("frequencyHz") is not None:
            band["centerFrequencyHz"] = dominant["frequencyHz"]

    analysis: dict[str, Any] = {
        "analysisId": f"{signal['signalId']}-frequency-analysis",
        "domain": semantics["frequencyDomain"],
        "method": "fft" if spectrum_payload["status"] == "computed" else "unknown",
        "sourceQuantity": signal["quantity"],
        "bands": [band],
        "peaks": peaks,
        "description": f"Frequency metadata for {signal['label']} in the loaded public observation snapshot.",
        "assumptions": list(spectrum_payload["assumptions"]),
        "limitations": list(spectrum_payload["limitations"]),
    }
    signal_spectrum = spectrum_payload.get("signalSpectrum") if isinstance(spectrum_payload.get("signalSpectrum"), dict) else None
    if signal_spectrum is not None:
        analysis["sampleRateHz"] = signal_spectrum["sampleRateHz"]
        analysis["windowSeconds"] = signal_spectrum["timeRange"][1] - signal_spectrum["timeRange"][0]
        if len(frequencies) > 1:
            analysis["frequencyResolutionHz"] = frequencies[1] - frequencies[0]
    return analysis


def _diagnostic_artifact(
    snapshot: dict[str, Any],
    signal: dict[str, Any],
    summary: dict[str, Any],
    spectrum_payload: dict[str, Any],
) -> dict[str, Any]:
    semantics = _signal_semantics(signal)
    artifact_id = f"public-signal-{signal['signalId']}"
    return {
        "kind": "openplazma.diagnostic_artifact",
        "version": VERSION,
        "artifactId": artifact_id,
        "artifactKind": "signal_series",
        "label": f"{signal['label']} public signal window",
        "provenanceKind": "measured",
        "instrument": {
            "instrumentKind": semantics["instrumentKind"],
            "label": f"{snapshot['provider']} public data product for {signal['label']}",
            "observables": [semantics["observable"]],
            "calibration": {
                "status": "unknown",
                "responseKnown": False,
                "correctionApplied": False,
                "description": "OpenPlazma loaded a frozen public data product and did not import an independent instrument response model.",
                "limitations": [
                    "Calibration provenance is not sufficient for source identity or fusion-condition claims.",
                    "No local facility telemetry or control channel is involved.",
                ],
            },
        },
        "contributions": [
            {
                "contributionKind": "unknown",
                "role": "candidate",
                "status": "unresolved",
                "description": "The public signal can contain source variability, propagation effects, and data-product processing effects.",
                "limitations": ["Contributions are not separated by this evidence package."],
            },
            {
                "contributionKind": "instrument_noise",
                "role": "noise",
                "status": "unresolved",
                "description": "Instrument and public product processing noise may contribute to the signal.",
                "limitations": ["OpenPlazma does not attach an instrument noise model for this snapshot."],
            },
        ],
        "companionChannels": [
            {
                "channelId": f"channel-{signal['signalId']}",
                "signalId": signal["signalId"],
                "label": signal["label"],
                "role": "primary",
                "observable": semantics["observable"],
                "quantity": signal["quantity"],
                "unit": signal["unit"],
                "limitations": ["Public data-product channel; no independent calibration model is attached."],
            }
        ],
        "signalWindows": [
            {
                "windowId": f"window-{signal['signalId']}",
                "signalId": signal["signalId"],
                "channelId": f"channel-{signal['signalId']}",
                "role": "primary",
                "timeRange": summary["timeRange"],
                "sampleCount": summary["pointCount"],
                "description": "Selected time window from the loaded public observation snapshot.",
                "limitations": ["The window is descriptive and does not establish a fusion condition."],
            }
        ],
        "frequencyAnalyses": [_frequency_analysis(signal, spectrum_payload)],
        "source": {
            "sourceKind": "public_snapshot",
            "label": snapshot["provenance"]["sourceLabel"],
            "uri": snapshot["provenancePath"],
            "signalIds": [signal["signalId"]],
            "sha256": snapshot["provenance"]["bundleSha256"],
            "limitations": list(snapshot["provenance"]["limitations"]),
        },
        "sourceUri": snapshot["recordPath"],
        "signalIds": [signal["signalId"]],
        "quantity": signal["quantity"],
        "unit": signal["unit"],
        "description": f"Diagnostic signal window for {signal['label']} from a frozen public observation snapshot.",
        "limitations": [
            "Measured public data-product signal only.",
            "No calibrated fusion product or fusion-condition evidence is attached.",
            "This artifact cannot support a positive fusion claim by itself.",
        ],
    }


def _observation_statement(signal: dict[str, Any], summary: dict[str, Any], spectrum_payload: dict[str, Any]) -> dict[str, Any]:
    semantics = _signal_semantics(signal)
    dominant = spectrum_payload.get("dominantPeak") if isinstance(spectrum_payload.get("dominantPeak"), dict) else None
    computed = dominant is not None and dominant.get("frequencyHz") is not None
    return {
        "kind": "openplazma.observation_statement",
        "version": VERSION,
        "readoutId": f"readout-{signal['signalId']}",
        "artifactId": f"public-signal-{signal['signalId']}",
        "signalId": signal["signalId"],
        "observable": semantics["observable"],
        "readoutKind": "frequency_peak" if computed else "frequency_band",
        "method": "fft" if computed else "signal_window_summary",
        "selector": f"timeRange={summary['timeRange'][0]}..{summary['timeRange'][1]}",
        "timeRange": summary["timeRange"],
        "value": dominant["frequencyHz"] if computed else summary["mean"],
        "textValue": (
            f"{signal['label']} has descriptive signal-window and frequency metadata; "
            "it is not calibrated fusion product or fusion-condition evidence."
        ),
        "unit": "Hz" if computed else signal["unit"],
        "status": "candidate" if computed else "inconclusive",
        "uncertainty": "No independent instrument-response uncertainty is attached.",
        "assumptions": [
            "The public snapshot was loaded from local frozen repository files.",
            "Signal values are treated as public data-product measurements.",
        ],
        "limitations": [
            "The readout is mediated by a public data product and OpenPlazma normalization.",
            "The readout does not support a positive fusion claim without calibrated product or condition evidence.",
        ],
        "alternatives": [
            "public data-product processing effects",
            "instrument noise or background",
            "ordinary solar wind or X-ray variability",
        ],
    }


def _claim(signal: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "openplazma.investigation_claim",
        "version": VERSION,
        "claimId": f"claim-{signal['signalId']}-fusion-unsupported",
        "claimType": "fusion_status",
        "statement": (
            f"{signal['label']} public signal-window evidence does not support a fusion claim "
            "without calibrated fusion product or condition evidence."
        ),
        "status": "support",
        "evidenceArtifactIds": [f"public-signal-{signal['signalId']}"],
        "evidenceReadoutIds": [f"readout-{signal['signalId']}"],
        "method": "evidence_gap_review",
        "assumptions": ["The loaded public snapshot is the evidence boundary for this claim."],
        "limitations": [
            "This is a conservative support claim about evidential insufficiency, not a source-identity claim.",
            "Absence of calibrated product evidence is not treated as proof of absence.",
        ],
        "alternatives": [
            "additional calibrated product diagnostics could change the disposition",
            "additional calibrated condition measurements could change the disposition",
        ],
    }


def _target(snapshot: dict[str, Any]) -> dict[str, Any]:
    record = require_mapping(snapshot["record"], "PublicObservationSnapshot.record")
    shot = require_mapping(record["shot"], "PublicObservationSnapshot.record.shot")
    return {
        "kind": "openplazma.investigation_target",
        "version": VERSION,
        "targetId": snapshot["shotId"],
        "targetKind": "unknown",
        "label": shot["displayName"],
        "description": "Frozen public observation dataset loaded for read-only diagnostic investigation.",
        "candidateEnergySources": ["unknown", "plasma", "fusion"],
        "limitations": [
            "Target is a public observation snapshot, not a controllable facility.",
            "The snapshot does not directly measure fusion reaction products or full fusion conditions.",
        ],
    }


def _questions() -> list[dict[str, Any]]:
    return [
        {
            "questionId": "q-public-source-classification",
            "questionKind": "energy_source_classification",
            "text": "Which source claims are supported by the loaded public observation evidence?",
        },
        {
            "questionId": "q-public-fusion-status",
            "questionKind": "is_fusion",
            "text": "Does the evidence support a fusion claim under conservative diagnostic standards?",
        },
        {
            "questionId": "q-public-fusion-conditions",
            "questionKind": "fusion_conditions",
            "text": "Which calibrated product or condition observations would be needed before strengthening the fusion disposition?",
        },
    ]


def _fusion_assessment(package_id: str, artifact_ids: list[str], readout_ids: list[str]) -> dict[str, Any]:
    return {
        "kind": "openplazma.fusion_condition_assessment",
        "version": VERSION,
        "assessmentId": f"{package_id}-fusion-assessment",
        "fusionStatus": "unsupported",
        "conditionMode": "forward_from_observations",
        "reactionCandidates": ["unknown"],
        "observedOrInferredConditions": [],
        "requiredConditions": [
            {
                "parameter": "ion_temperature",
                "status": "unknown",
                "logicalRole": "necessary",
                "evidenceArtifactIds": artifact_ids,
                "evidenceReadoutIds": readout_ids,
                "assumptions": [],
                "limitations": ["No calibrated ion-temperature condition evidence is present in the public snapshot package."],
            },
            {
                "parameter": "density",
                "status": "unknown",
                "logicalRole": "necessary",
                "evidenceArtifactIds": artifact_ids,
                "evidenceReadoutIds": readout_ids,
                "assumptions": [],
                "limitations": ["No calibrated fusion-relevant density condition evidence is present in the public snapshot package."],
            },
            {
                "parameter": "confinement_time",
                "status": "unknown",
                "logicalRole": "necessary",
                "evidenceArtifactIds": artifact_ids,
                "evidenceReadoutIds": readout_ids,
                "assumptions": [],
                "limitations": ["No confinement condition evidence is present in the public snapshot package."],
            },
        ],
        "unknowns": [
            "calibrated fusion product evidence",
            "calibrated ion temperature",
            "fusion-relevant density",
            "confinement time",
            "source identity",
        ],
        "assumptions": ["The loaded public snapshot is the complete evidence boundary for this assessment."],
        "limitations": [
            "Unsupported means this public snapshot lacks calibrated fusion product or condition evidence.",
            "This assessment does not establish that fusion is absent.",
        ],
    }


def _required_observables(signals: Sequence[dict[str, Any]]) -> list[str]:
    observed = [_signal_semantics(signal)["observable"] for signal in signals]
    return _dedupe([*observed, *PRODUCT_REQUIRED_OBSERVABLES])


def build_public_observation_campaign(
    snapshot: dict[str, Any],
    *,
    signal_ids: Sequence[str] | None = None,
    time_window: Sequence[float] | None = None,
    max_frequency_hz: float | None = None,
    session_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build a generic investigation session/report from a loaded public snapshot."""
    selected_snapshot = require_mapping(deepcopy(snapshot), "PublicObservationSnapshot")
    selected_signals = _selected_signals(selected_snapshot, signal_ids)
    signal_index = build_signal_channel_index(selected_signals, time_windows=[time_window] if time_window is not None else None)

    summaries = [_window_summary(signal, time_window) for signal in selected_signals]
    spectra = [
        _spectrum_payload(signal, time_window=time_window, max_frequency_hz=max_frequency_hz)
        for signal in selected_signals
    ]
    artifacts = [
        _diagnostic_artifact(selected_snapshot, signal, summary, spectrum)
        for signal, summary, spectrum in zip(selected_signals, summaries, spectra, strict=True)
    ]
    observations = [
        _observation_statement(signal, summary, spectrum)
        for signal, summary, spectrum in zip(selected_signals, summaries, spectra, strict=True)
    ]
    claims = [_claim(signal) for signal in selected_signals]
    package_id = f"public-observation-{selected_snapshot['shotId']}"
    fusion_assessment = _fusion_assessment(
        package_id,
        [artifact["artifactId"] for artifact in artifacts],
        [observation["readoutId"] for observation in observations],
    )
    package = build_investigation_package(
        package_id=package_id,
        title=f"Public observation investigation for {selected_snapshot['shotId']}",
        target=_target(selected_snapshot),
        questions=_questions(),
        artifacts=artifacts,
        observations=observations,
        fusion_assessment=fusion_assessment,
        claims=claims,
        limitations=[
            *selected_snapshot["limitations"],
            "Investigation package is built from a local frozen public snapshot; no network fetch is performed.",
            "No facility telemetry read or facility control path is present.",
        ],
    )
    session = create_investigation_session(
        session_id=session_id or f"session-{package_id}",
        package=package,
        required_observables=_required_observables(selected_signals),
        created_at=created_at,
        updated_at=created_at,
        limitations=[
            "Read-only public observation investigation session.",
            "No facility telemetry read, facility control, live network fetch, or hosted execution path.",
        ],
    )
    report = create_investigation_session_report(
        session,
        created_at=created_at,
        next_observations=[
            "Add calibrated fusion-product evidence such as neutron_flux or gamma_ray before any stronger fusion claim.",
            "Add calibrated condition measurements for temperature, density, and confinement time before assessing fusion conditions.",
            "Cross-check the frozen public snapshot against independent calibrated public data products while keeping the workflow read-only.",
        ],
    )
    reported_session = record_investigation_report(session, report, updated_at=created_at)
    assessment = assess_investigation_session(reported_session)

    return {
        "kind": "openplazma.public_observation_campaign",
        "version": VERSION,
        "snapshot": {
            "datasetId": selected_snapshot["datasetId"],
            "provider": selected_snapshot["provider"],
            "shotId": selected_snapshot["shotId"],
            "recordPath": selected_snapshot["recordPath"],
            "provenancePath": selected_snapshot["provenancePath"],
            "sourceLabel": selected_snapshot["provenance"]["sourceLabel"],
            "bundleSha256": selected_snapshot["provenance"]["bundleSha256"],
        },
        "signals": [_signal_ref(signal) for signal in selected_signals],
        "signalIndex": signal_index,
        "signalSummaries": summaries,
        "spectra": spectra,
        "package": reported_session["package"],
        "session": reported_session,
        "assessment": assessment,
        "report": report,
        "limitations": [
            "Campaign was built from already-loaded public snapshot data.",
            "Campaign does not perform network access or interact with facility telemetry/control.",
        ],
    }


def log_public_observation_campaign(
    run: Run,
    campaign: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    content_addressed: bool = False,
) -> dict[str, Any]:
    selected_campaign = require_mapping(campaign, "PublicObservationCampaign")
    selected_snapshot = require_mapping(snapshot, "PublicObservationSnapshot")
    metadata = {
        "provider": selected_snapshot["provider"],
        "shotId": selected_snapshot["shotId"],
        "datasetId": selected_snapshot["datasetId"],
        "sourceLabel": selected_snapshot["provenance"]["sourceLabel"],
        "sha256": selected_snapshot["provenance"]["bundleSha256"],
    }
    artifacts: dict[str, Any] = {
        "public_snapshot": run.log_artifact(
            "public_snapshot",
            "public_observation_snapshot",
            {
                "kind": "openplazma.public_observation_snapshot",
                "version": VERSION,
                "datasetId": selected_snapshot["datasetId"],
                "provider": selected_snapshot["provider"],
                "shotId": selected_snapshot["shotId"],
                "recordPath": selected_snapshot["recordPath"],
                "provenancePath": selected_snapshot["provenancePath"],
                "record": selected_snapshot["record"],
                "capabilities": selected_snapshot["capabilities"],
                "limitations": selected_snapshot["limitations"],
            },
            metadata,
            content_addressed=content_addressed,
        ),
        "source_provenance": run.log_artifact(
            "source_provenance",
            "source_provenance",
            selected_snapshot["provenance"],
            metadata,
            content_addressed=content_addressed,
        ),
        "signal_index": run.log_artifact(
            "signal_index",
            "signal_channel_index",
            selected_campaign["signalIndex"],
            metadata,
            content_addressed=content_addressed,
        ),
    }

    selected_signal_ids = [signal["signalId"] for signal in selected_campaign["signals"]]
    signals_by_id = {signal["signalId"]: signal for signal in selected_snapshot["signals"]}
    for signal_id in selected_signal_ids:
        signal = validate_signal_series(signals_by_id[signal_id])
        signal_metadata = {
            **metadata,
            "signal": _signal_ref(signal),
            "signalId": signal_id,
            "quantity": signal["quantity"],
            "unit": signal["unit"],
        }
        artifacts[f"signal_series:{signal_id}"] = run.log_artifact(
            f"signal_series_{signal_id}",
            "signal_series",
            signal,
            signal_metadata,
            content_addressed=content_addressed,
        )

    for spectrum in selected_campaign["spectra"]:
        signal_id = spectrum["sourceSignalId"]
        signal_ref = next(signal for signal in selected_campaign["signals"] if signal["signalId"] == signal_id)
        artifacts[f"signal_spectrum:{signal_id}"] = run.log_artifact(
            f"signal_spectrum_{signal_id}",
            "signal_spectrum",
            spectrum,
            {
                **metadata,
                "signal": signal_ref,
                "spectrum": spectrum["spectrum"],
            },
            content_addressed=content_addressed,
        )

    investigation_artifacts = log_investigation_session(
        run,
        selected_campaign["session"],
        assessment=selected_campaign["assessment"],
        report=selected_campaign["report"],
        content_addressed=content_addressed,
    )
    artifacts.update(investigation_artifacts)
    return artifacts


def run_public_observation_campaign(
    *,
    repo_root: str | Path,
    run_store: str | Path,
    output_dir: str | Path | None = None,
    shot_id: str | None = None,
    signal_ids: Sequence[str] | None = None,
    time_window: Sequence[float] | None = None,
    max_frequency_hz: float | None = None,
    clean: bool = False,
) -> dict[str, Any]:
    selected_run_store = Path(run_store)
    if clean and selected_run_store.exists():
        shutil.rmtree(selected_run_store)
    snapshot = load_public_observation_snapshot(repo_root, shot_id)
    campaign = build_public_observation_campaign(
        snapshot,
        signal_ids=signal_ids,
        time_window=time_window,
        max_frequency_hz=max_frequency_hz,
    )
    with start_run(
        project="openplazma-public-observation",
        campaign="public-observation-campaign",
        run_type="public_observation_investigation",
        context=snapshot["record"]["context"],
        config={
            "source": "public_observation_campaign",
            "shotId": snapshot["shotId"],
            "signalIds": [signal["signalId"] for signal in campaign["signals"]],
        },
        run_store=selected_run_store,
    ) as run:
        artifacts = log_public_observation_campaign(run, campaign, snapshot)
        assessment = campaign["assessment"]
        run.log_metric("public_signal_count", len(snapshot["signals"]))
        run.log_metric("selected_signal_count", len(campaign["signals"]))
        run.log_metric("diagnostic_artifact_count", len(campaign["package"]["artifacts"]))
        run.log_metric("observation_statement_count", len(campaign["package"].get("observations", [])))
        run.log_metric("missing_required_observable_count", len(assessment["measurementAssessment"]["missingObservables"]))
        run.log_metric("investigation_report_count", assessment["reportCount"])
        for summary in campaign["signalSummaries"]:
            run.log_metric(
                f"signal_points_{summary['signalId']}",
                summary["pointCount"],
                metadata={
                    "signal": {
                        "signalId": summary["signalId"],
                        "quantity": summary["quantity"],
                        "unit": summary["unit"],
                    }
                },
            )
        run_id = run.run_id

    observatory_path = export_observatory_html(run_store=selected_run_store, output_dir=output_dir)
    run_path = selected_run_store / "runs" / run_id
    report_artifact = artifacts["investigation_report"]
    return {
        "kind": "openplazma.public_observation_campaign_run",
        "version": VERSION,
        "runId": run_id,
        "runPath": run_path.as_posix(),
        "runStorePath": selected_run_store.as_posix(),
        "observatoryPath": observatory_path.as_posix(),
        "reportArtifactPath": (run_path / report_artifact["path"]).as_posix(),
        "artifactRecords": artifacts,
        "campaign": campaign,
    }
