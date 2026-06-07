from __future__ import annotations

import csv
import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import validate_experiment_context
from .signals import validate_signal_series

LOCAL_SIGNAL_LIMITATIONS = [
    "LOCAL_SIGNAL_FILE read-only import.",
    "Source schema validated; physical provenance and calibration are not validated by OpenPlazma.",
    "Read-only analysis and decision support.",
    "No command/control path or hazardous operating procedure.",
    "Not a standalone authority for safety-critical operation or reactor design decisions.",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv_signal(path: Path, time_column: str, value_column: str) -> tuple[list[float], list[float]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("CSV signal file must include a header row.")
        if time_column not in reader.fieldnames:
            raise ValueError(f"CSV signal file is missing time column '{time_column}'.")
        if value_column not in reader.fieldnames:
            raise ValueError(f"CSV signal file is missing value column '{value_column}'.")

        time: list[float] = []
        values: list[float] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                time_value = float(row[time_column] or "")
                signal_value = float(row[value_column] or "")
            except ValueError as error:
                raise ValueError(f"CSV signal file contains a non-numeric value on row {row_number}.") from error
            if not math.isfinite(time_value) or not math.isfinite(signal_value):
                raise ValueError(f"CSV signal file contains a non-finite value on row {row_number}.")
            time.append(time_value)
            values.append(signal_value)
    return time, values


def import_local_signal_csv(
    path: str | Path,
    *,
    signal_id: str,
    label: str,
    quantity: str,
    unit: str,
    time_column: str = "time",
    value_column: str = "value",
    shot_id: str | None = None,
    project_id: str = "openplazma-local",
    dataset_id: str | None = None,
    source_label: str | None = None,
    source_uri: str | None = None,
    description: str | None = None,
    created_at: str | None = None,
    observations: list[dict[str, Any] | str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    source_path = Path(path)
    if not source_path.is_file():
        raise ValueError("Local signal CSV path must be an existing file.")

    time, values = _read_csv_signal(source_path, time_column, value_column)
    signal = validate_signal_series(
        {
            "kind": "openplazma.signal_series",
            "version": "0.1.0",
            "signalId": signal_id,
            "label": label,
            "quantity": quantity,
            "unit": unit,
            "timeUnit": "s",
            "time": time,
            "values": values,
        }
    )

    selected_shot_id = shot_id or source_path.stem
    selected_dataset_id = dataset_id or f"local-{selected_shot_id}"
    selected_created_at = created_at or _now()
    selected_source_label = source_label or f"Local signal file: {source_path.name}"
    selected_source_uri = source_uri or f"local-file:{source_path.name}"
    selected_limitations = limitations or list(LOCAL_SIGNAL_LIMITATIONS)
    normalized_observations = [
        {"text": observation} if isinstance(observation, str) else dict(observation)
        for observation in observations or []
    ]

    context = validate_experiment_context(
        {
            "kind": "openplazma.experiment_context",
            "version": "0.1.0",
            "contextId": f"ctx-{selected_shot_id}-{signal_id}",
            "projectId": project_id,
            "datasetId": selected_dataset_id,
            "description": description or f"Read-only local signal import for {signal_id}.",
            "safetyClassification": "read-only-local-signal",
            "createdAt": selected_created_at,
            "target": {
                "type": "local_run_store",
                "id": ".openplazma",
                "label": "Local OpenPlazma RunStore",
            },
            "source": {
                "provider": "LOCAL_SIGNAL_FILE",
                "sourceLabel": selected_source_label,
                "uri": selected_source_uri,
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
            "signals": [
                {
                    "signalId": signal["signalId"],
                    "label": signal["label"],
                    "quantity": signal["quantity"],
                    "unit": signal["unit"],
                }
            ],
            "view": {"timeRange": [signal["time"][0], signal["time"][-1]]},
            "observations": normalized_observations,
            "limitations": selected_limitations,
        }
    )
    return {"context": context, "signal": signal}
