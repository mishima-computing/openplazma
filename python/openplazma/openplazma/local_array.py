"""Read-only importer for a multi-channel magnetic-probe array CSV.

Turns a real CSV (one time column + one column per Mirnov probe) into a
schema-validated study record carrying a DiagnosticArray and an inferred
mode number / rotation / locking, computed in-process. Read-only:
LOCAL_SIGNAL_FILE provenance, capabilities all-false, no facility access.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from .context import validate_experiment_context
from .local_signal import LOCAL_SIGNAL_LIMITATIONS, _now, _sha256
from .mhd import validate_mhd_analysis_bundle
from .mhd_analysis import build_inference_from_array
from .signals import validate_signal_series

TWO_PI = 2 * math.pi


def _read_csv_columns(path: Path, time_column: str, value_columns: list[str]) -> tuple[list[float], dict[str, list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("CSV array file must include a header row.")
        for column in [time_column, *value_columns]:
            if column not in reader.fieldnames:
                raise ValueError(f"CSV array file is missing column '{column}'.")
        time: list[float] = []
        columns: dict[str, list[float]] = {column: [] for column in value_columns}
        for row_number, row in enumerate(reader, start=2):
            try:
                t = float(row[time_column] or "")
            except ValueError as error:
                raise ValueError(f"CSV array file has a non-numeric time on row {row_number}.") from error
            if not math.isfinite(t):
                raise ValueError(f"CSV array file has a non-finite time on row {row_number}.")
            time.append(t)
            for column in value_columns:
                try:
                    v = float(row[column] or "")
                except ValueError as error:
                    raise ValueError(f"CSV array file has a non-numeric value for '{column}' on row {row_number}.") from error
                if not math.isfinite(v):
                    raise ValueError(f"CSV array file has a non-finite value for '{column}' on row {row_number}.")
                columns[column].append(v)
    return time, columns


def import_mirnov_array_csv(
    path: str | Path,
    *,
    probes: list[dict[str, Any]],
    time_column: str = "time",
    quantity: str = "magnetic_fluctuation",
    unit: str = "a.u.",
    array_id: str = "mirnov-toroidal",
    array_label: str = "Mirnov toroidal array",
    array_kind: str = "mirnov_toroidal",
    major_radius_m: float = 1.5,
    island_width_gain: float | None = None,
    shot_id: str | None = None,
    project_id: str = "openplazma-local",
    dataset_id: str | None = None,
    source_label: str | None = None,
    source_uri: str | None = None,
    description: str | None = None,
    created_at: str | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    """Import a magnetic-probe array CSV and infer its dominant mode.

    ``probes`` is a list of dicts, one per probe, with at least ``column`` and
    ``toroidalAngleRad``; optional ``channelId``, ``label``, ``poloidalAngleRad``.
    """
    source_path = Path(path)
    if not source_path.is_file():
        raise ValueError("Local array CSV path must be an existing file.")
    if len(probes) < 2:
        raise ValueError("A diagnostic array needs at least two probes.")

    value_columns = [probe["column"] for probe in probes]
    time, columns = _read_csv_columns(source_path, time_column, value_columns)

    signals: list[dict[str, Any]] = []
    channels: list[dict[str, Any]] = []
    for index, probe in enumerate(probes):
        channel_id = probe.get("channelId", f"{array_id}-{index + 1:02d}")
        label = probe.get("label", f"Mirnov coil {index + 1:02d}")
        signal = validate_signal_series(
            {
                "kind": "openplazma.signal_series",
                "version": "0.1.0",
                "signalId": channel_id,
                "label": label,
                "quantity": quantity,
                "unit": unit,
                "timeUnit": "s",
                "time": time,
                "values": columns[probe["column"]],
            }
        )
        signals.append(signal)
        channels.append(
            {
                "kind": "openplazma.diagnostic_channel",
                "version": "0.1.0",
                "channelId": channel_id,
                "label": label,
                "signalId": channel_id,
                "diagnosticKind": "magnetic_probe",
                "geometry": {
                    "poloidalAngleRad": float(probe.get("poloidalAngleRad", 0.0)),
                    "toroidalAngleRad": float(probe["toroidalAngleRad"]),
                    "majorRadiusM": float(probe.get("majorRadiusM", major_radius_m)),
                },
            }
        )

    array = {
        "kind": "openplazma.diagnostic_array",
        "version": "0.1.0",
        "arrayId": array_id,
        "label": array_label,
        "arrayKind": array_kind,
        "channels": channels,
    }
    inference = build_inference_from_array(array, signals, island_width_gain=island_width_gain)
    n = inference["modeEstimate"]["toroidalModeNumber"]
    claim = {
        "kind": "openplazma.claim",
        "version": "0.1.0",
        "claimId": f"claim-{array_id}-mode",
        "statement": f"The imported array shows a dominant toroidal mode number n={n}.",
        "inferenceId": inference["inferenceId"],
        "evidence": [
            {
                "kind": "openplazma.evidence_link",
                "version": "0.1.0",
                "verdict": "support",
                "arrayId": array_id,
                "timeRange": [time[0], time[-1]],
                "rationale": f"Cross-probe phase fit recovers n={n} (confidence {inference['modeEstimate']['confidence']:.2f}).",
            }
        ],
    }
    mhd = {
        "kind": "openplazma.mhd_analysis_bundle",
        "version": "0.1.0",
        "provenanceKind": "measured",
        "arrays": [array],
        "events": [],
        "observationModels": [],
        "inferences": [inference],
        "claims": [claim],
    }

    selected_shot_id = shot_id or source_path.stem
    signal_refs = [
        {"signalId": s["signalId"], "label": s["label"], "quantity": s["quantity"], "unit": s["unit"]}
        for s in signals
    ]
    context = validate_experiment_context(
        {
            "kind": "openplazma.experiment_context",
            "version": "0.1.0",
            "contextId": f"ctx-{selected_shot_id}-{array_id}",
            "projectId": project_id,
            "datasetId": dataset_id or f"local-{selected_shot_id}",
            "description": description or f"Read-only local array import for {array_id}.",
            "safetyClassification": "read-only-local-signal",
            "createdAt": created_at or _now(),
            "target": {"type": "local_run_store", "id": ".openplazma", "label": "Local OpenPlazma RunStore"},
            "source": {
                "provider": "LOCAL_SIGNAL_FILE",
                "sourceLabel": source_label or f"Local array file: {source_path.name}",
                "uri": source_uri or f"local-file:{source_path.name}",
                "sha256": _sha256(source_path),
                "validationStatus": "schema_validated",
            },
            "capabilities": {
                "readData": True,
                "writeArtifacts": True,
                "runSimulation": False,
                "submitComputeJob": False,
                "readFacilityTelemetry": False,
                "controlFacility": False,
            },
            "shotRef": {"provider": "LOCAL_SIGNAL_FILE", "shotId": selected_shot_id},
            "signals": signal_refs,
            "view": {"timeRange": [time[0], time[-1]]},
            "observations": [],
            "limitations": limitations or list(LOCAL_SIGNAL_LIMITATIONS),
        }
    )

    validate_mhd_analysis_bundle(mhd, {s["signalId"] for s in signals})
    return {"context": context, "signals": signals, "array": array, "inference": inference, "mhd": mhd}
