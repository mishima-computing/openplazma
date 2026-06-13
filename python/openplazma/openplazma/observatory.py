from __future__ import annotations

import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any

from ._json import loads_json
from .observation_lineage import validate_observation_lineage_audit
from .runstore import describe_runstore_backend, load_artifacts, load_events, load_manifest, load_metrics, load_run

_RUN_ID_RE = re.compile(r"^OPR-\d{8}(?:-\d{6,}|-[A-Za-z0-9_.-]+-[a-f0-9]{12})$")
_SVG_RENDER_POINT_LIMIT = 80
_UNSAFE_CAPABILITY_FIELDS = {
    "runSimulation",
    "submitComputeJob",
    "readFacilityTelemetry",
    "controlFacility",
}
_LINEAGE_AUDIT_ARTIFACT_TYPE = "observation_lineage_audit"
_LINEAGE_AUDIT_KIND = "openplazma.observation_lineage_audit"


def _run_store_root(run_store: str | Path) -> Path:
    return Path(run_store)


def _runs_root(run_store: str | Path) -> Path:
    return _run_store_root(run_store) / "runs"


def _run_dir(run_id: str, run_store: str | Path) -> Path:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must look like a supported OPR id.")
    return _runs_root(run_store) / run_id


def _ensure_inside(parent: Path, child: Path) -> None:
    parent_resolved = parent.resolve()
    child_resolved = child.resolve()
    if parent_resolved != child_resolved and parent_resolved not in child_resolved.parents:
        raise ValueError("Observatory output path must remain inside its output directory.")


def _html(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return escape(json.dumps(value, sort_keys=True, allow_nan=False), quote=True)
    return escape(str(value), quote=True)


def _cell(value: Any) -> str:
    return f"<td>{_html(value)}</td>"


def _format_number(value: float) -> str:
    return f"{value:.6g}"


def _as_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _number_list(value: Any) -> list[float]:
    if not isinstance(value, list):
        return []
    values = []
    for item in value:
        number = _as_number(item)
        if number is None:
            return []
        values.append(number)
    return values


def _first_string(mapping: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _metadata_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _signal_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    signal = _metadata_mapping(metadata.get("signal"))
    return {
        "signalId": _first_string(signal, ["signalId", "id"]) or _first_string(metadata, ["signalId", "signal"]),
        "quantity": _first_string(signal, ["quantity"]) or _first_string(metadata, ["quantity"]),
        "unit": _first_string(signal, ["unit"]) or _first_string(metadata, ["unit"]),
    }


def _compact_item(value: Any) -> str:
    if isinstance(value, dict):
        for fields in (
            ["claimId", "status", "statement"],
            ["reportId", "status", "title"],
            ["artifactId", "status", "label"],
            ["readoutId", "status", "observable"],
            ["id", "status", "label"],
        ):
            selected = [str(value[field]) for field in fields if value.get(field) not in {None, ""}]
            if selected:
                return " | ".join(selected)
        return json.dumps(value, sort_keys=True, allow_nan=False)
    return str(value)


def _compact_list_html(value: Any, *, max_items: int = 6) -> str:
    if value is None:
        return ""
    items = value if isinstance(value, list) else [value]
    rendered = "".join(f"<li>{_html(_compact_item(item))}</li>" for item in items[:max_items])
    if len(items) > max_items:
        rendered += f"<li>{_html(f'+{len(items) - max_items} more')}</li>"
    return f'<ul class="compact-list">{rendered}</ul>' if rendered else ""


def _decimate_svg_points(points: list[tuple[int, float]]) -> list[tuple[int, float]]:
    if len(points) <= _SVG_RENDER_POINT_LIMIT:
        return points
    stride = max(1, (len(points) + _SVG_RENDER_POINT_LIMIT - 1) // _SVG_RENDER_POINT_LIMIT)
    selected = points[::stride]
    if selected[-1] != points[-1]:
        selected.append(points[-1])
    return selected


def _metric_series_svg(points: list[tuple[int, float]], label: str) -> str:
    numeric_points = _decimate_svg_points(points)
    if not numeric_points:
        return ""
    width = 220
    height = 52
    padding = 6
    values = [value for _, value in numeric_points]
    minimum = min(values)
    maximum = max(values)
    span = maximum - minimum
    denominator = max(1, len(numeric_points) - 1)
    svg_points = []
    for index, (_, value) in enumerate(numeric_points):
        x = padding + (width - 2 * padding) * index / denominator
        y = height / 2 if span == 0 else height - padding - ((value - minimum) / span) * (height - 2 * padding)
        svg_points.append((x, y))
    point_attr = " ".join(f"{_format_number(x)},{_format_number(y)}" for x, y in svg_points)
    circles = "".join(
        f'<circle cx="{_format_number(x)}" cy="{_format_number(y)}" r="2.4"></circle>' for x, y in svg_points
    )
    return (
        f'<svg class="sparkline" viewBox="0 0 {width} {height}" role="img" aria-label="{_html(label)}">'
        f'<polyline points="{point_attr}"></polyline>{circles}</svg>'
    )


def _capability_class(key: str, value: Any) -> str:
    if key in _UNSAFE_CAPABILITY_FIELDS and value is True:
        return "unsafe"
    if value is True:
        return "safe"
    return "false"


def _safe_artifact_href(run_id: str, artifact_path: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must look like a supported OPR id.")
    artifact_parts = Path(artifact_path).parts
    if (
        Path(artifact_path).is_absolute()
        or not artifact_path.startswith("artifacts/")
        or "\\" in artifact_path
        or ".." in artifact_parts
        or any(":" in part for part in artifact_parts)
    ):
        raise ValueError("Artifact path must remain under artifacts/.")
    return f"../../runs/{run_id}/{escape(artifact_path, quote=True)}"


def _artifact_file_for_read(run_id: str, artifact: dict[str, Any], run_store: str | Path) -> Path:
    artifact_path = artifact.get("path", "")
    _safe_artifact_href(run_id, artifact_path)
    run_dir = _run_dir(run_id, run_store)
    selected = run_dir / artifact_path
    _ensure_inside(run_dir / "artifacts", selected)
    return selected


def _load_json_artifact_payload(run_id: str, artifact: dict[str, Any], run_store: str | Path) -> dict[str, Any] | None:
    artifact_path = _artifact_file_for_read(run_id, artifact, run_store)
    try:
        payload = loads_json(artifact_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _json_type_name(value: Any) -> str:
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def _load_lineage_audit_payload(
    run_id: str,
    artifact: dict[str, Any],
    run_store: str | Path,
) -> tuple[dict[str, Any] | None, str | None]:
    artifact_path = _artifact_file_for_read(run_id, artifact, run_store)
    try:
        raw_payload = artifact_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return None, (
            "Invalid observation_lineage_audit artifact payload: "
            f"artifact file is unreadable ({error.__class__.__name__})."
        )
    try:
        payload = loads_json(raw_payload)
    except ValueError as error:
        return None, (
            "Invalid observation_lineage_audit artifact payload: "
            f"malformed JSON ({error.__class__.__name__})."
        )
    if not isinstance(payload, dict):
        return None, (
            "Invalid observation_lineage_audit artifact payload: "
            f"expected JSON object, found {_json_type_name(payload)}."
        )
    if payload.get("kind") != _LINEAGE_AUDIT_KIND:
        found_kind = payload.get("kind")
        found = f"{found_kind!r}" if found_kind is not None else "missing"
        return None, (
            "Invalid observation_lineage_audit artifact kind: "
            f"expected {_LINEAGE_AUDIT_KIND}, found {found}."
        )
    try:
        return validate_observation_lineage_audit(payload, require_passed=False), None
    except ValueError as error:
        return None, (
            "Invalid observation_lineage_audit artifact payload: "
            f"schema validation failed ({error})."
        )


def _validate_run_exists(run_id: str, run_store: str | Path) -> Path:
    run_dir = _run_dir(run_id, run_store)
    if not (run_dir / "run.json").is_file():
        raise FileNotFoundError(f"Run {run_id} was not found in {run_store}.")
    return run_dir


def _load_observatory_run(run_id: str, run_store: str | Path) -> dict[str, Any]:
    _validate_run_exists(run_id, run_store)
    return load_run(run_id, run_store=run_store)


def summarize_run(run_id: str, run_store: str | Path = ".openplazma") -> dict[str, Any]:
    run = _load_observatory_run(run_id, run_store=run_store)
    manifest = load_manifest(run_id, run_store=run_store)
    metrics = load_metrics(run_id, run_store=run_store)
    return {
        "runId": run["runId"],
        "project": run["project"],
        "campaign": run["campaign"],
        "runType": run["runType"],
        "status": run["status"],
        "createdAt": run["createdAt"],
        "finishedAt": run.get("finishedAt"),
        "sourceProvider": run["source"]["provider"],
        "targetType": run["target"]["type"],
        "artifactCount": len(manifest.get("artifacts", [])),
        "metricCount": len(metrics),
    }


def summarize_runstore(run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    runs_root = _runs_root(run_store)
    if not runs_root.exists():
        raise FileNotFoundError(f"No RunStore runs directory found at {runs_root}.")
    run_ids = sorted(path.name for path in runs_root.iterdir() if path.is_dir() and _RUN_ID_RE.fullmatch(path.name))
    if not run_ids:
        raise FileNotFoundError(f"No RunStore runs found at {runs_root}.")
    return [summarize_run(run_id, run_store=run_store) for run_id in run_ids]


def load_run_artifacts(run_id: str, run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    return load_artifacts(run_id, run_store=run_store)


def load_run_events(run_id: str, run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    return load_events(run_id, run_store=run_store)


def _latest_metrics_by_name(metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for metric in metrics:
        name = metric.get("name")
        if isinstance(name, str):
            latest[name] = metric
    return latest


def _is_numeric_metric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _metric_series_summary(
    run_pages: list[tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]],
) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for run_index, (run_id, _run, metrics, _artifacts, _events) in enumerate(run_pages):
        latest = _latest_metrics_by_name(metrics)
        for name, metric in latest.items():
            value = metric.get("value")
            if not _is_numeric_metric(value):
                continue
            metadata = _metadata_mapping(metric.get("metadata"))
            signal = _signal_metadata(metadata)
            row = by_name.setdefault(
                name,
                {
                    "name": name,
                    "signalId": signal.get("signalId"),
                    "quantity": signal.get("quantity") or name,
                    "unit": signal.get("unit"),
                    "points": [],
                },
            )
            if row.get("signalId") is None and signal.get("signalId") is not None:
                row["signalId"] = signal["signalId"]
            if row.get("unit") is None and signal.get("unit") is not None:
                row["unit"] = signal["unit"]
            row["points"].append(
                {
                    "runIndex": run_index,
                    "runId": run_id,
                    "value": value,
                    "createdAt": metric.get("createdAt"),
                    "metadata": metadata,
                }
            )

    series = []
    for row in by_name.values():
        values = [float(point["value"]) for point in row["points"]]
        row["min"] = min(values)
        row["max"] = max(values)
        row["latestValue"] = row["points"][-1]["value"]
        series.append(row)
    return sorted(series, key=lambda row: row["name"])


def _spectrum_mapping(metadata: dict[str, Any]) -> dict[str, Any] | None:
    spectrum = metadata.get("spectrum")
    if isinstance(spectrum, dict):
        return spectrum
    if metadata.get("spectrumKind") is not None or any(
        key in metadata for key in ["frequenciesHz", "frequencyHz", "wavelengthsNm", "wavelengthNm", "energiesKeV", "bins", "channels"]
    ):
        return metadata
    return None


def _spectrum_axis_values(spectrum: dict[str, Any], keys: list[str]) -> tuple[str | None, list[float]]:
    for key in keys:
        values = _number_list(spectrum.get(key))
        if values:
            return key, values
    return None, []


def _spectrum_stats(spectrum: dict[str, Any]) -> dict[str, Any]:
    x_key, x_values = _spectrum_axis_values(
        spectrum,
        ["frequenciesHz", "frequencyHz", "wavelengthsNm", "wavelengthNm", "energiesKeV", "bins", "channels", "x"],
    )
    y_key, y_values = _spectrum_axis_values(spectrum, ["values", "counts", "amplitudes", "intensity", "y"])
    point_count = len(y_values) if y_values else len(x_values)
    peak_x = None
    peak_y = None
    if y_values:
        peak_index = max(range(len(y_values)), key=lambda index: y_values[index])
        peak_y = y_values[peak_index]
        if x_values and peak_index < len(x_values):
            peak_x = x_values[peak_index]
    return {
        "domain": _first_string(spectrum, ["domain", "frequencyDomain", "spectrumDomain"]),
        "xKey": x_key,
        "yKey": y_key,
        "xUnit": _first_string(spectrum, ["xUnit", "frequencyUnit", "wavelengthUnit", "energyUnit"]),
        "yUnit": _first_string(spectrum, ["yUnit", "unit"]),
        "pointCount": point_count,
        "peakX": peak_x,
        "peakY": peak_y,
    }


def _spectral_row_from_spectrum(
    *,
    run_id: str,
    source_kind: str,
    source_name: str,
    metadata: dict[str, Any],
) -> dict[str, Any] | None:
    spectrum = _spectrum_mapping(metadata)
    if spectrum is None:
        return None
    signal = _signal_metadata(metadata)
    stats = _spectrum_stats(spectrum)
    return {
        "runId": run_id,
        "sourceKind": source_kind,
        "sourceName": source_name,
        "signalId": signal.get("signalId"),
        "quantity": signal.get("quantity") or _first_string(metadata, ["quantity"]) or source_name,
        "unit": signal.get("unit") or stats.get("yUnit"),
        **stats,
    }


def _spectral_rows_from_frequency_analyses(run_id: str, source_name: str, analyses: Any) -> list[dict[str, Any]]:
    rows = []
    if not isinstance(analyses, list):
        return rows
    for analysis in analyses:
        if not isinstance(analysis, dict):
            continue
        peaks = analysis.get("peaks") if isinstance(analysis.get("peaks"), list) else []
        bands = analysis.get("bands") if isinstance(analysis.get("bands"), list) else []
        peak = next((item for item in peaks if isinstance(item, dict)), {})
        rows.append(
            {
                "runId": run_id,
                "sourceKind": "artifact",
                "sourceName": source_name,
                "signalId": None,
                "quantity": analysis.get("sourceQuantity"),
                "unit": peak.get("unit") if isinstance(peak, dict) else None,
                "domain": analysis.get("domain"),
                "xKey": "frequencyHz" if peak.get("frequencyHz") is not None else None,
                "yKey": "amplitude" if peak.get("amplitude") is not None else None,
                "xUnit": "Hz" if peak.get("frequencyHz") is not None else None,
                "yUnit": None,
                "pointCount": len(peaks) + len(bands),
                "peakX": peak.get("frequencyHz") if isinstance(peak, dict) else None,
                "peakY": peak.get("amplitude") if isinstance(peak, dict) else None,
            }
        )
    return rows


def _spectral_rows_for_artifact_payload(run_id: str, artifact: dict[str, Any], payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    artifact_name = str(artifact.get("name", "artifact"))
    metadata_row = _spectral_row_from_spectrum(
        run_id=run_id,
        source_kind="artifact",
        source_name=artifact_name,
        metadata=_metadata_mapping(artifact.get("metadata")),
    )
    if metadata_row is not None:
        rows.append(metadata_row)
    if payload is None:
        return rows

    payload_row = _spectral_row_from_spectrum(
        run_id=run_id,
        source_kind="artifact",
        source_name=artifact_name,
        metadata=payload,
    )
    if payload_row is not None:
        rows.append(payload_row)
    rows.extend(_spectral_rows_from_frequency_analyses(run_id, artifact_name, payload.get("frequencyAnalyses")))
    for diagnostic in payload.get("artifacts", []) if isinstance(payload.get("artifacts"), list) else []:
        if not isinstance(diagnostic, dict):
            continue
        label = diagnostic.get("label") or diagnostic.get("artifactId") or artifact_name
        rows.extend(_spectral_rows_from_frequency_analyses(run_id, str(label), diagnostic.get("frequencyAnalyses")))
    return rows


def _spectral_rows_summary(
    run_pages: list[tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]],
    run_store: str | Path,
) -> list[dict[str, Any]]:
    rows = []
    for run_id, _run, metrics, artifacts, _events in run_pages:
        for metric in metrics:
            metric_row = _spectral_row_from_spectrum(
                run_id=run_id,
                source_kind="metric",
                source_name=str(metric.get("name", "metric")),
                metadata=_metadata_mapping(metric.get("metadata")),
            )
            if metric_row is not None:
                rows.append(metric_row)
        for artifact in artifacts:
            payload = _load_json_artifact_payload(run_id, artifact, run_store)
            rows.extend(_spectral_rows_for_artifact_payload(run_id, artifact, payload))
    return rows


def _evidence_spine_from_mapping(value: dict[str, Any]) -> dict[str, Any] | None:
    spine = value.get("evidenceSpine")
    if isinstance(spine, dict):
        return {
            "sessionStatus": spine.get("sessionStatus"),
            "targetKind": spine.get("targetKind"),
            "fusionStatus": spine.get("fusionStatus"),
            "conditionMode": spine.get("conditionMode"),
            "missingObservables": spine.get("missingObservables", []),
            "unresolvedArtifacts": spine.get("unresolvedArtifacts", []),
            "claims": spine.get("claims", []),
            "reports": spine.get("reports", []),
            "nextObservations": spine.get("nextObservations", []),
        }
    if any(
        key in value
        for key in [
            "sessionStatus",
            "targetKind",
            "fusionStatus",
            "conditionMode",
            "missingObservables",
            "unresolvedArtifacts",
            "nextObservations",
        ]
    ):
        return {
            "sessionStatus": value.get("sessionStatus"),
            "targetKind": value.get("targetKind"),
            "fusionStatus": value.get("fusionStatus"),
            "conditionMode": value.get("conditionMode"),
            "missingObservables": value.get("missingObservables", []),
            "unresolvedArtifacts": value.get("unresolvedArtifacts", []),
            "claims": value.get("claims", []),
            "reports": value.get("reports", []),
            "nextObservations": value.get("nextObservations", []),
        }
    return None


def _unresolved_diagnostic_artifacts(package: dict[str, Any]) -> list[dict[str, Any]]:
    unresolved = []
    artifacts = package.get("artifacts") if isinstance(package.get("artifacts"), list) else []
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        calibration = _metadata_mapping(_metadata_mapping(artifact.get("instrument")).get("calibration"))
        contributions = artifact.get("contributions") if isinstance(artifact.get("contributions"), list) else []
        has_unresolved_contribution = any(
            isinstance(contribution, dict) and contribution.get("status") == "unresolved"
            for contribution in contributions
        )
        if (
            artifact.get("provenanceKind") == "unknown"
            or has_unresolved_contribution
            or calibration.get("status") in {"uncalibrated", "unknown"}
        ):
            unresolved.append(
                {
                    "artifactId": artifact.get("artifactId"),
                    "status": calibration.get("status") or artifact.get("provenanceKind"),
                    "label": artifact.get("label"),
                }
            )
    return unresolved


def _evidence_spine_from_investigation_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    explicit = _evidence_spine_from_mapping(payload)
    if explicit is not None:
        return explicit
    kind = payload.get("kind")
    if kind == "openplazma.investigation_package":
        assessment = _metadata_mapping(payload.get("fusionAssessment"))
        target = _metadata_mapping(payload.get("target"))
        return {
            "sessionStatus": payload.get("sessionStatus") or "package",
            "targetKind": target.get("targetKind"),
            "fusionStatus": assessment.get("fusionStatus"),
            "conditionMode": assessment.get("conditionMode"),
            "missingObservables": assessment.get("unknowns", []),
            "unresolvedArtifacts": _unresolved_diagnostic_artifacts(payload),
            "claims": payload.get("claims", []),
            "reports": payload.get("reports", []),
            "nextObservations": payload.get("nextObservations", []),
        }
    if kind == "openplazma.investigation_report":
        return {
            "sessionStatus": payload.get("sessionStatus") or "report",
            "targetKind": payload.get("targetKind"),
            "fusionStatus": payload.get("fusionStatus"),
            "conditionMode": payload.get("conditionMode"),
            "missingObservables": payload.get("missingObservables", []),
            "unresolvedArtifacts": payload.get("unresolvedArtifacts", []),
            "claims": payload.get("claims", []),
            "reports": [{"reportId": payload.get("reportId"), "status": payload.get("sessionStatus"), "title": payload.get("packageId")}],
            "nextObservations": payload.get("nextObservations", []),
        }
    return None


def _evidence_spine_summary(
    run_pages: list[tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]],
    run_store: str | Path,
) -> list[dict[str, Any]]:
    rows = []
    for run_id, _run, _metrics, artifacts, _events in run_pages:
        for artifact in artifacts:
            spine = _evidence_spine_from_mapping(_metadata_mapping(artifact.get("metadata")))
            payload = _load_json_artifact_payload(run_id, artifact, run_store)
            if spine is None and payload is not None:
                spine = _evidence_spine_from_investigation_payload(payload)
            if spine is None:
                continue
            rows.append(
                {
                    "runId": run_id,
                    "artifactName": artifact.get("name"),
                    "artifactType": artifact.get("type"),
                    "artifactPath": artifact.get("path"),
                    **spine,
                }
            )
    return rows


def _lineage_audit_row_from_payload(run_id: str, artifact: dict[str, Any], payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None or payload.get("kind") != _LINEAGE_AUDIT_KIND:
        return None
    calibration = _metadata_mapping(payload.get("calibrationSummary"))
    fusion = _metadata_mapping(payload.get("fusionAssessment"))
    spectrum_statuses = sorted(
        {
            row.get("status")
            for row in payload.get("spectrumLineage", [])
            if isinstance(row, dict) and row.get("status") is not None
        }
    )
    claim_admissibility = sorted(
        {
            row.get("admissibility")
            for row in payload.get("claimAudits", [])
            if isinstance(row, dict) and row.get("admissibility") is not None
        }
    )
    return {
        "runId": run_id,
        "artifactName": artifact.get("name"),
        "artifactType": artifact.get("type"),
        "artifactPath": artifact.get("path"),
        "partitionId": payload.get("partitionId"),
        "auditStatus": payload.get("status"),
        "calibrationStatus": calibration.get("status"),
        "spectrumStatuses": spectrum_statuses,
        "claimAdmissibility": claim_admissibility,
        "missingObservables": fusion.get("missingObservables", []),
        "failureReasons": payload.get("failureReasons", []),
    }


def _failed_lineage_audit_row(run_id: str, artifact: dict[str, Any], failure_reason: str) -> dict[str, Any]:
    return {
        "runId": run_id,
        "artifactName": artifact.get("name"),
        "artifactType": artifact.get("type"),
        "artifactPath": artifact.get("path"),
        "partitionId": None,
        "auditStatus": "failed",
        "calibrationStatus": None,
        "spectrumStatuses": [],
        "claimAdmissibility": [],
        "missingObservables": [],
        "failureReasons": [failure_reason],
    }


def _lineage_audit_summary(
    run_pages: list[tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]],
    run_store: str | Path,
) -> list[dict[str, Any]]:
    rows = []
    for run_id, _run, _metrics, artifacts, _events in run_pages:
        for artifact in artifacts:
            if artifact.get("type") == _LINEAGE_AUDIT_ARTIFACT_TYPE:
                payload, failure_reason = _load_lineage_audit_payload(run_id, artifact, run_store)
                if failure_reason is not None:
                    rows.append(_failed_lineage_audit_row(run_id, artifact, failure_reason))
                    continue
            else:
                payload = _load_json_artifact_payload(run_id, artifact, run_store)
                if payload is not None and payload.get("kind") == _LINEAGE_AUDIT_KIND:
                    rows.append(
                        _failed_lineage_audit_row(
                            run_id,
                            artifact,
                            "Invalid observation_lineage_audit artifact manifest type: "
                            f"expected {_LINEAGE_AUDIT_ARTIFACT_TYPE}, found {artifact.get('type')!r}.",
                        )
                    )
                    continue
            row = _lineage_audit_row_from_payload(run_id, artifact, payload)
            if row is not None:
                rows.append(row)
    return rows


def _build_multirun_summary(
    summaries: list[dict[str, Any]],
    run_pages: list[tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]],
    run_store: str | Path,
) -> dict[str, Any]:
    return {
        "kind": "openplazma.observatory_multi_run_summary",
        "version": "0.1.0",
        "backend": describe_runstore_backend(run_store),
        "runCount": len(summaries),
        "runs": summaries,
        "metricSeries": _metric_series_summary(run_pages),
        "spectralRows": _spectral_rows_summary(run_pages, run_store),
        "evidenceSpines": _evidence_spine_summary(run_pages, run_store),
        "lineageAudits": _lineage_audit_summary(run_pages, run_store),
    }


def summarize_runstore_multirun(run_store: str | Path = ".openplazma") -> dict[str, Any]:
    summaries, run_pages = _collect_observatory_data(run_store=run_store)
    return _build_multirun_summary(summaries, run_pages, run_store)


def summarize_metric_comparison(run_a_metrics: list[dict[str, Any]], run_b_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    a_latest = _latest_metrics_by_name(run_a_metrics)
    b_latest = _latest_metrics_by_name(run_b_metrics)
    rows = []
    for name in sorted(set(a_latest) | set(b_latest)):
        a_metric = a_latest.get(name)
        b_metric = b_latest.get(name)
        a_value = a_metric.get("value") if a_metric else None
        b_value = b_metric.get("value") if b_metric else None
        delta = None
        if a_metric is None:
            status = "only_in_b"
        elif b_metric is None:
            status = "only_in_a"
        elif _is_numeric_metric(a_value) and _is_numeric_metric(b_value):
            delta = b_value - a_value
            status = "same" if a_value == b_value else "different"
        elif a_value == b_value:
            status = "same"
        else:
            status = "non_numeric"
        rows.append(
            {
                "name": name,
                "runAValue": a_value,
                "runBValue": b_value,
                "delta": delta,
                "status": status,
            }
        )
    return rows


def _artifact_key(artifact: dict[str, Any]) -> str:
    return f"{artifact.get('name', '')}::{artifact.get('type', '')}"


def summarize_artifact_comparison(run_a_artifacts: list[dict[str, Any]], run_b_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    a_by_key = {_artifact_key(artifact): artifact for artifact in run_a_artifacts}
    b_by_key = {_artifact_key(artifact): artifact for artifact in run_b_artifacts}
    rows = []
    for key in sorted(set(a_by_key) | set(b_by_key)):
        a_artifact = a_by_key.get(key)
        b_artifact = b_by_key.get(key)
        if a_artifact is None:
            status = "only_in_b"
        elif b_artifact is None:
            status = "only_in_a"
        elif a_artifact.get("sha256") == b_artifact.get("sha256"):
            status = "same_hash"
        else:
            status = "different_hash"
        rows.append(
            {
                "key": key,
                "runA": a_artifact,
                "runB": b_artifact,
                "status": status,
            }
        )
    return rows


def _field_comparison(run_a: dict[str, Any], run_b: dict[str, Any], fields: list[tuple[str, str]]) -> list[dict[str, Any]]:
    rows = []
    for label, path in fields:
        a_value = _nested_get(run_a, path)
        b_value = _nested_get(run_b, path)
        rows.append(
            {
                "field": label,
                "runAValue": a_value,
                "runBValue": b_value,
                "status": "same" if a_value == b_value else "different",
            }
        )
    return rows


def _nested_get(mapping: dict[str, Any], dotted_path: str) -> Any:
    value: Any = mapping
    for part in dotted_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def summarize_capability_comparison(run_a: dict[str, Any], run_b: dict[str, Any]) -> list[dict[str, Any]]:
    capability_fields = [
        ("capabilities.readData", "capabilities.readData"),
        ("capabilities.writeArtifacts", "capabilities.writeArtifacts"),
        ("capabilities.runSimulation", "capabilities.runSimulation"),
        ("capabilities.submitComputeJob", "capabilities.submitComputeJob"),
        ("capabilities.readFacilityTelemetry", "capabilities.readFacilityTelemetry"),
        ("capabilities.controlFacility", "capabilities.controlFacility"),
    ]
    rows = _field_comparison(run_a, run_b, capability_fields)
    for row in rows:
        unsafe_field = row["field"] in {
            "capabilities.runSimulation",
            "capabilities.submitComputeJob",
            "capabilities.readFacilityTelemetry",
            "capabilities.controlFacility",
        }
        row["safetyStatus"] = "unsafe_true" if unsafe_field and (row["runAValue"] is True or row["runBValue"] is True) else "safe"
    return rows


def _source_target_comparison(run_a: dict[str, Any], run_b: dict[str, Any]) -> list[dict[str, Any]]:
    return _field_comparison(
        run_a,
        run_b,
        [
            ("source.provider", "source.provider"),
            ("source.sourceLabel", "source.sourceLabel"),
            ("source.inspiredBy", "source.inspiredBy"),
            ("target.type", "target.type"),
            ("target.id", "target.id"),
            ("target.label", "target.label"),
        ],
    )


def _limitations_comparison(run_a: dict[str, Any], run_b: dict[str, Any]) -> dict[str, Any]:
    a_limitations = run_a.get("limitations", [])
    b_limitations = run_b.get("limitations", [])
    if not isinstance(a_limitations, list):
        a_limitations = []
    if not isinstance(b_limitations, list):
        b_limitations = []
    return {
        "runALimitations": a_limitations,
        "runBLimitations": b_limitations,
        "status": "same" if a_limitations == b_limitations else "different",
    }


def compare_runs(run_a_id: str, run_b_id: str, run_store: str | Path = ".openplazma") -> dict[str, Any]:
    if run_a_id == run_b_id:
        raise ValueError("compare_runs requires two distinct run IDs.")
    run_a = _load_observatory_run(run_a_id, run_store)
    run_b = _load_observatory_run(run_b_id, run_store)
    metrics_a = load_metrics(run_a_id, run_store=run_store)
    metrics_b = load_metrics(run_b_id, run_store=run_store)
    artifacts_a = load_run_artifacts(run_a_id, run_store=run_store)
    artifacts_b = load_run_artifacts(run_b_id, run_store=run_store)
    return {
        "runA": run_a,
        "runB": run_b,
        "metrics": summarize_metric_comparison(metrics_a, metrics_b),
        "artifacts": summarize_artifact_comparison(artifacts_a, artifacts_b),
        "sourceTarget": _source_target_comparison(run_a, run_b),
        "capabilities": summarize_capability_comparison(run_a, run_b),
        "limitations": _limitations_comparison(run_a, run_b),
    }


def _write_css(output_dir: Path) -> None:
    css_path = output_dir / "assets" / "observatory.css"
    _ensure_inside(output_dir, css_path)
    css_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.write_text(
        """body{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;color:#17202a;background:#f7f8fa}main{max-width:1180px;margin:0 auto;padding:32px 20px}h1,h2{color:#101820}a{color:#0b5cad}table{border-collapse:collapse;width:100%;margin:16px 0;background:#fff}th,td{border:1px solid #d7dce2;padding:8px 10px;text-align:left;vertical-align:top}th{background:#edf1f5}.panel{background:#fff;border:1px solid #d7dce2;padding:16px;margin:16px 0}.safe{color:#116329;font-weight:600}.false{color:#5f6b7a}.unsafe{color:#a61b1b;font-weight:700}.meta{color:#52606d}.compact-list{margin:0;padding-left:18px}.sparkline{width:220px;height:52px;overflow:visible}.sparkline polyline{fill:none;stroke:#0b5cad;stroke-width:2.2}.sparkline circle{fill:#fff;stroke:#0b5cad;stroke-width:1.8}.nowrap{white-space:nowrap}code{background:#eef2f6;padding:2px 4px}""",
        encoding="utf-8",
    )


def _page(title: str, body: str, stylesheet: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_html(title)}</title>\n"
        f'<link rel="stylesheet" href="{stylesheet}">\n'
        "</head>\n"
        "<body><main>\n"
        f"{body}\n"
        "</main></body>\n"
        "</html>\n"
    )


def _backend_html(backend: dict[str, Any]) -> str:
    scheduler = _metadata_mapping(backend.get("scheduler"))
    query_capabilities = _metadata_mapping(backend.get("queryCapabilities"))
    capability_rows = "\n".join(
        "<tr>"
        + _cell(key)
        + f'<td class="{_capability_class(key, value)}">{_html(value)}</td>'
        + "</tr>"
        for key, value in query_capabilities.items()
    )
    return (
        '<section class="panel"><h2>RunStore Backend</h2>'
        + _mapping_table(
            {
                "backendKind": backend.get("backendKind"),
                "objectStore": _metadata_mapping(backend.get("objectStore")).get("kind"),
                "indexDb": _metadata_mapping(backend.get("indexDb")).get("kind"),
                "scheduler": scheduler.get("kind"),
                "remoteExecution": scheduler.get("remoteExecution"),
                "submitComputeJob": scheduler.get("submitComputeJob"),
            }
        )
        + "<h2>Query Capabilities</h2><table><tbody>"
        + capability_rows
        + "</tbody></table></section>\n"
    )


def _metric_series_html(series: list[dict[str, Any]]) -> str:
    if not series:
        return ""
    rows = []
    for metric in series:
        points = [
            (int(point["runIndex"]), float(point["value"]))
            for point in metric.get("points", [])
            if _as_number(point.get("value")) is not None
        ]
        chart = _metric_series_svg(points, f"Metric trend for {metric.get('name')}")
        values = [
            f"{point.get('runId')}: {_format_number(float(point.get('value')))}"
            for point in metric.get("points", [])[-4:]
            if _as_number(point.get("value")) is not None
        ]
        rows.append(
            "<tr>"
            + _cell(metric.get("name"))
            + _cell(metric.get("signalId"))
            + _cell(metric.get("quantity"))
            + _cell(metric.get("unit"))
            + _cell(metric.get("min"))
            + _cell(metric.get("max"))
            + f"<td>{chart}</td>"
            + f"<td>{_compact_list_html(values, max_items=4)}</td>"
            + "</tr>"
        )
    return (
        "<h2>Metric Trends</h2><table><thead><tr>"
        "<th>Name</th><th>Signal</th><th>Quantity</th><th>Unit</th><th>Min</th><th>Max</th><th>Chart</th><th>Recent Values</th>"
        "</tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>\n"
    )


def _spectral_rows_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    html_rows = "\n".join(
        "<tr>"
        + _cell(row.get("runId"))
        + _cell(row.get("sourceKind"))
        + _cell(row.get("sourceName"))
        + _cell(row.get("signalId"))
        + _cell(row.get("domain"))
        + _cell(row.get("quantity"))
        + _cell(row.get("pointCount"))
        + _cell(row.get("xKey"))
        + _cell(row.get("yKey"))
        + _cell(row.get("peakX"))
        + _cell(row.get("peakY"))
        + "</tr>"
        for row in rows
    )
    return (
        "<h2>Spectral Metadata</h2><table><thead><tr>"
        "<th>Run</th><th>Source</th><th>Name</th><th>Signal</th><th>Domain</th><th>Quantity</th><th>Points</th>"
        "<th>X</th><th>Y</th><th>Peak X</th><th>Peak Y</th>"
        "</tr></thead><tbody>"
        + html_rows
        + "</tbody></table>\n"
    )


def _evidence_spines_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    html_rows = "\n".join(
        "<tr>"
        + _cell(row.get("runId"))
        + _cell(row.get("artifactName"))
        + _cell(row.get("sessionStatus"))
        + _cell(row.get("targetKind"))
        + _cell(row.get("fusionStatus"))
        + _cell(row.get("conditionMode"))
        + f"<td>{_compact_list_html(row.get('missingObservables'))}</td>"
        + f"<td>{_compact_list_html(row.get('unresolvedArtifacts'))}</td>"
        + f"<td>{_compact_list_html(row.get('claims'))}</td>"
        + f"<td>{_compact_list_html(row.get('reports'))}</td>"
        + f"<td>{_compact_list_html(row.get('nextObservations'))}</td>"
        + "</tr>"
        for row in rows
    )
    return (
        "<h2>Investigation Evidence Spine</h2><table><thead><tr>"
        "<th>Run</th><th>Artifact</th><th>Session</th><th>Target</th><th>Fusion</th><th>Condition Mode</th>"
        "<th>Missing Observables</th><th>Unresolved Artifacts</th><th>Claims</th><th>Reports</th><th>Next Observations</th>"
        "</tr></thead><tbody>"
        + html_rows
        + "</tbody></table>\n"
    )


def _lineage_audits_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    html_rows = "\n".join(
        "<tr>"
        + _cell(row.get("runId"))
        + _cell(row.get("partitionId"))
        + _cell(row.get("auditStatus"))
        + _cell(row.get("calibrationStatus"))
        + f"<td>{_compact_list_html(row.get('spectrumStatuses'))}</td>"
        + f"<td>{_compact_list_html(row.get('claimAdmissibility'))}</td>"
        + f"<td>{_compact_list_html(row.get('missingObservables'))}</td>"
        + f"<td>{_compact_list_html(row.get('failureReasons'))}</td>"
        + "</tr>"
        for row in rows
    )
    return (
        "<h2>Lineage Audit</h2><table><thead><tr>"
        "<th>Run</th><th>Partition</th><th>Audit</th><th>Calibration</th><th>Spectrum</th>"
        "<th>Claim Admissibility</th><th>Missing Observables</th><th>Failure Reasons</th>"
        "</tr></thead><tbody>"
        + html_rows
        + "</tbody></table>\n"
    )


def _index_html(multirun_summary: dict[str, Any]) -> str:
    summaries = multirun_summary["runs"]
    rows = "\n".join(
        "<tr>"
        f'<td><a href="runs/{_html(summary["runId"])}.html">{_html(summary["runId"])}</a></td>'
        + _cell(summary["project"])
        + _cell(summary["campaign"])
        + _cell(summary["runType"])
        + _cell(summary["status"])
        + _cell(summary["createdAt"])
        + _cell(summary["finishedAt"])
        + _cell(summary["sourceProvider"])
        + _cell(summary["targetType"])
        + _cell(summary["artifactCount"])
        + _cell(summary["metricCount"])
        + "</tr>"
        for summary in summaries
    )
    body = (
        "<h1>OpenPlazma Observatory</h1>\n"
        '<p class="meta">Read-only local report for inspectable OpenPlazma RunStore records.</p>\n'
        + _backend_html(multirun_summary["backend"])
        + "<table><thead><tr>"
        "<th>Run</th><th>Project</th><th>Campaign</th><th>Run Type</th><th>Status</th>"
        "<th>Created</th><th>Finished</th><th>Source</th><th>Target</th><th>Artifacts</th><th>Metrics</th>"
        "</tr></thead><tbody>\n"
        f"{rows}\n"
        "</tbody></table>"
        + _metric_series_html(multirun_summary["metricSeries"])
        + _spectral_rows_html(multirun_summary["spectralRows"])
        + _lineage_audits_html(multirun_summary["lineageAudits"])
        + _evidence_spines_html(multirun_summary["evidenceSpines"])
    )
    return _page("OpenPlazma Observatory", body, "assets/observatory.css")


def _mapping_table(mapping: dict[str, Any]) -> str:
    rows = "\n".join(f"<tr><th>{_html(key)}</th>{_cell(value)}</tr>" for key, value in mapping.items())
    return f"<table><tbody>{rows}</tbody></table>"


def _run_detail_html(
    run: dict[str, Any],
    metrics: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    events: list[dict[str, Any]],
    run_store: str | Path | None = None,
) -> str:
    run_pages = [(run["runId"], run, metrics, artifacts, events)]
    spectral_rows = _spectral_rows_summary(run_pages, run_store) if run_store is not None else []
    evidence_spines = _evidence_spine_summary(run_pages, run_store) if run_store is not None else []
    lineage_audits = _lineage_audit_summary(run_pages, run_store) if run_store is not None else []
    capabilities_rows = "\n".join(
        f'<tr><th>{_html(key)}</th><td class="{_capability_class(key, value)}">{_html(value)}</td></tr>'
        for key, value in run["capabilities"].items()
    )
    metric_rows = "\n".join(
        "<tr>"
        + _cell(metric.get("name"))
        + _cell(metric.get("value"))
        + _cell(metric.get("step"))
        + _cell(metric.get("createdAt"))
        + _cell(metric.get("metadata", {}))
        + "</tr>"
        for metric in metrics
    )
    artifact_rows = "\n".join(
        "<tr>"
        + _cell(artifact.get("name"))
        + _cell(artifact.get("type"))
        + f'<td><a href="{_safe_artifact_href(run["runId"], artifact.get("path", ""))}">{_html(artifact.get("path"))}</a></td>'
        + _cell(artifact.get("sha256"))
        + _cell(artifact.get("metadata", {}))
        + "</tr>"
        for artifact in artifacts
    )
    event_rows = "\n".join(
        "<tr>"
        + _cell(event.get("eventType"))
        + _cell(event.get("createdAt"))
        + _cell(event.get("message"))
        + _cell(event.get("metadata", {}))
        + "</tr>"
        for event in events
    )
    body = (
        f"<h1>Run {_html(run['runId'])}</h1>\n"
        '<p><a href="../index.html">Back to Observatory index</a></p>\n'
        '<section class="panel"><h2>Run Metadata</h2>'
        + _mapping_table(
            {
                "project": run["project"],
                "campaign": run["campaign"],
                "runType": run["runType"],
                "status": run["status"],
                "createdAt": run["createdAt"],
                "updatedAt": run["updatedAt"],
                "finishedAt": run.get("finishedAt"),
            }
        )
        + "</section>\n"
        '<section class="panel"><h2>Source</h2>'
        + _mapping_table(run["source"])
        + "</section>\n"
        '<section class="panel"><h2>Target</h2>'
        + _mapping_table(run["target"])
        + "</section>\n"
        '<section class="panel"><h2>Capabilities</h2><table><tbody>'
        + capabilities_rows
        + "</tbody></table></section>\n"
        '<section class="panel"><h2>Limitations</h2><ul>'
        + "".join(f"<li>{_html(item)}</li>" for item in run["limitations"])
        + "</ul></section>\n"
        "<h2>Metrics</h2><table><thead><tr><th>Name</th><th>Value</th><th>Step</th><th>Created</th><th>Metadata</th></tr></thead><tbody>"
        + metric_rows
        + "</tbody></table>\n"
        + "<h2>Artifacts</h2><table><thead><tr><th>Name</th><th>Type</th><th>Path</th><th>SHA-256</th><th>Metadata</th></tr></thead><tbody>"
        + artifact_rows
        + "</tbody></table>\n"
        + _spectral_rows_html(spectral_rows)
        + _lineage_audits_html(lineage_audits)
        + _evidence_spines_html(evidence_spines)
        + "<h2>Events</h2><table><thead><tr><th>Type</th><th>Created</th><th>Message</th><th>Metadata</th></tr></thead><tbody>"
        + event_rows
        + "</tbody></table>\n"
    )
    return _page(f"OpenPlazma Run {run['runId']}", body, "../assets/observatory.css")


def _collect_observatory_data(run_store: str | Path) -> tuple[list[dict[str, Any]], list[tuple[str, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]]]:
    summaries = summarize_runstore(run_store=run_store)
    run_pages = []
    for summary in summaries:
        run_id = summary["runId"]
        run = _load_observatory_run(run_id, run_store=run_store)
        metrics = load_metrics(run_id, run_store=run_store)
        artifacts = load_run_artifacts(run_id, run_store=run_store)
        events = load_run_events(run_id, run_store=run_store)
        run_pages.append((run_id, run, metrics, artifacts, events))
    return summaries, run_pages


def _compare_file_name(run_a_id: str, run_b_id: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_a_id) or not _RUN_ID_RE.fullmatch(run_b_id):
        raise ValueError("Compare run IDs must look like supported OPR ids.")
    return f"{run_a_id}__vs__{run_b_id}.html"


def _run_compare_summary(run: dict[str, Any]) -> str:
    return _mapping_table(
        {
            "runId": run.get("runId"),
            "project": run.get("project"),
            "campaign": run.get("campaign"),
            "runType": run.get("runType"),
            "status": run.get("status"),
            "createdAt": run.get("createdAt"),
            "finishedAt": run.get("finishedAt"),
        }
    )


def _comparison_rows(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        "<tr>"
        + _cell(row.get("field"))
        + _cell(row.get("runAValue"))
        + _cell(row.get("runBValue"))
        + _cell(row.get("status"))
        + "</tr>"
        for row in rows
    )


def _capability_rows(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        "<tr>"
        + _cell(row.get("field"))
        + _cell(row.get("runAValue"))
        + _cell(row.get("runBValue"))
        + f'<td class="{"unsafe" if row.get("safetyStatus") == "unsafe_true" else "safe"}">{_html(row.get("safetyStatus"))}</td>'
        + _cell(row.get("status"))
        + "</tr>"
        for row in rows
    )


def _metric_comparison_rows(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        "<tr>"
        + _cell(row.get("name"))
        + _cell(row.get("runAValue"))
        + _cell(row.get("runBValue"))
        + _cell(row.get("delta"))
        + _cell(row.get("status"))
        + "</tr>"
        for row in rows
    )


def _artifact_link_cell(run_id: str, artifact: dict[str, Any] | None) -> str:
    if artifact is None:
        return "<td></td>"
    path = artifact.get("path", "")
    href = _safe_artifact_href(run_id, path)
    return f'<td><a href="{href}">{_html(path)}</a></td>'


def _artifact_comparison_rows(rows: list[dict[str, Any]], run_a_id: str, run_b_id: str) -> str:
    html_rows = []
    for row in rows:
        a_artifact = row.get("runA")
        b_artifact = row.get("runB")
        html_rows.append(
            "<tr>"
            + _cell(row.get("key"))
            + _artifact_link_cell(run_a_id, a_artifact)
            + _artifact_link_cell(run_b_id, b_artifact)
            + _cell(a_artifact.get("sha256") if a_artifact else None)
            + _cell(b_artifact.get("sha256") if b_artifact else None)
            + _cell(row.get("status"))
            + "</tr>"
        )
    return "\n".join(html_rows)


def _limitations_html(limitations: dict[str, Any]) -> str:
    a_items = "".join(f"<li>{_html(item)}</li>" for item in limitations["runALimitations"])
    b_items = "".join(f"<li>{_html(item)}</li>" for item in limitations["runBLimitations"])
    return (
        f'<p>Status: <strong>{_html(limitations["status"])}</strong></p>'
        "<table><thead><tr><th>Run A</th><th>Run B</th></tr></thead><tbody><tr>"
        f"<td><ul>{a_items}</ul></td><td><ul>{b_items}</ul></td>"
        "</tr></tbody></table>"
    )


def _compare_html(comparison: dict[str, Any]) -> str:
    run_a = comparison["runA"]
    run_b = comparison["runB"]
    run_a_id = run_a["runId"]
    run_b_id = run_b["runId"]
    body = (
        f"<h1>Compare Runs {_html(run_a_id)} and {_html(run_b_id)}</h1>\n"
        '<p><a href="../index.html">Back to Observatory index</a></p>\n'
        '<section class="panel"><h2>Run A</h2>'
        f'<p><a href="../runs/{_html(run_a_id)}.html">Open Run A detail</a></p>'
        + _run_compare_summary(run_a)
        + "</section>\n"
        '<section class="panel"><h2>Run B</h2>'
        f'<p><a href="../runs/{_html(run_b_id)}.html">Open Run B detail</a></p>'
        + _run_compare_summary(run_b)
        + "</section>\n"
        "<h2>Metric Comparison</h2><table><thead><tr><th>Name</th><th>Run A Latest Value</th><th>Run B Latest Value</th><th>Delta</th><th>Status</th></tr></thead><tbody>"
        + _metric_comparison_rows(comparison["metrics"])
        + "</tbody></table>\n"
        "<h2>Artifact Comparison</h2><table><thead><tr><th>Artifact Key</th><th>Run A Path</th><th>Run B Path</th><th>Run A SHA-256</th><th>Run B SHA-256</th><th>Status</th></tr></thead><tbody>"
        + _artifact_comparison_rows(comparison["artifacts"], run_a_id, run_b_id)
        + "</tbody></table>\n"
        "<h2>Source and Target Comparison</h2><table><thead><tr><th>Field</th><th>Run A</th><th>Run B</th><th>Status</th></tr></thead><tbody>"
        + _comparison_rows(comparison["sourceTarget"])
        + "</tbody></table>\n"
        "<h2>Capability Comparison</h2><table><thead><tr><th>Capability</th><th>Run A</th><th>Run B</th><th>Safety</th><th>Status</th></tr></thead><tbody>"
        + _capability_rows(comparison["capabilities"])
        + "</tbody></table>\n"
        '<section class="panel"><h2>Limitations Comparison</h2>'
        + _limitations_html(comparison["limitations"])
        + "</section>\n"
    )
    return _page(f"OpenPlazma Compare {run_a_id} vs {run_b_id}", body, "../assets/observatory.css")


def export_observatory_html(run_store: str | Path = ".openplazma", output_dir: str | Path | None = None) -> Path:
    summaries, run_pages = _collect_observatory_data(run_store=run_store)
    multirun_summary = _build_multirun_summary(summaries, run_pages, run_store)
    selected_output = Path(output_dir) if output_dir is not None else _run_store_root(run_store) / "observatory"
    selected_output.mkdir(parents=True, exist_ok=True)
    _write_css(selected_output)

    index_path = selected_output / "index.html"
    _ensure_inside(selected_output, index_path)
    index_path.write_text(_index_html(multirun_summary), encoding="utf-8")

    runs_dir = selected_output / "runs"
    _ensure_inside(selected_output, runs_dir)
    if runs_dir.exists():
        shutil.rmtree(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    compare_dir = selected_output / "compare"
    _ensure_inside(selected_output, compare_dir)
    if compare_dir.exists():
        shutil.rmtree(compare_dir)

    for run_id, run, metrics, artifacts, events in run_pages:
        run_page = runs_dir / f"{run_id}.html"
        _ensure_inside(selected_output, run_page)
        run_page.write_text(_run_detail_html(run, metrics, artifacts, events, run_store), encoding="utf-8")

    return selected_output


def export_observatory_compare_html(
    run_a_id: str,
    run_b_id: str,
    run_store: str | Path = ".openplazma",
    output_dir: str | Path | None = None,
) -> Path:
    comparison = compare_runs(run_a_id, run_b_id, run_store=run_store)
    selected_output = export_observatory_html(run_store=run_store, output_dir=output_dir)
    compare_dir = selected_output / "compare"
    _ensure_inside(selected_output, compare_dir)
    compare_dir.mkdir(parents=True, exist_ok=True)

    compare_path = compare_dir / _compare_file_name(run_a_id, run_b_id)
    _ensure_inside(compare_dir, compare_path)
    compare_path.write_text(_compare_html(comparison), encoding="utf-8")
    return compare_path
