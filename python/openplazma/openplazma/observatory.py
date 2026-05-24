from __future__ import annotations

import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any

from .runstore import load_manifest, load_metrics

_RUN_ID_RE = re.compile(r"^OPR-\d{8}-\d{6}$")
_UNSAFE_CAPABILITY_FIELDS = {
    "runSimulation",
    "submitComputeJob",
    "readFacilityTelemetry",
    "controlFacility",
}


def _run_store_root(run_store: str | Path) -> Path:
    return Path(run_store)


def _runs_root(run_store: str | Path) -> Path:
    return _run_store_root(run_store) / "runs"


def _run_dir(run_id: str, run_store: str | Path) -> Path:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must look like OPR-YYYYMMDD-000001.")
    return _runs_root(run_store) / run_id


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object in {path}.")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"Expected JSON object line in {path}.")
                records.append(value)
    return records


def _ensure_inside(parent: Path, child: Path) -> None:
    parent_resolved = parent.resolve()
    child_resolved = child.resolve()
    if parent_resolved != child_resolved and parent_resolved not in child_resolved.parents:
        raise ValueError("Observatory output path must remain inside its output directory.")


def _html(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return escape(json.dumps(value, sort_keys=True), quote=True)
    return escape(str(value), quote=True)


def _cell(value: Any) -> str:
    return f"<td>{_html(value)}</td>"


def _capability_class(key: str, value: Any) -> str:
    if key in _UNSAFE_CAPABILITY_FIELDS and value is True:
        return "unsafe"
    if value is True:
        return "safe"
    return "false"


def _safe_artifact_href(run_id: str, artifact_path: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must look like OPR-YYYYMMDD-000001.")
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


def _validate_run_exists(run_id: str, run_store: str | Path) -> Path:
    run_dir = _run_dir(run_id, run_store)
    if not (run_dir / "run.json").is_file():
        raise FileNotFoundError(f"Run {run_id} was not found in {run_store}.")
    return run_dir


def _load_observatory_run(run_id: str, run_store: str | Path) -> dict[str, Any]:
    run_dir = _validate_run_exists(run_id, run_store)
    run = _load_json(run_dir / "run.json")
    if run.get("runId") != run_id:
        raise ValueError(f"RunRecord runId does not match {run_id}.")
    return run


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
    manifest = load_manifest(run_id, run_store=run_store)
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("Run manifest artifacts must be a list.")
    return artifacts


def load_run_events(run_id: str, run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    return _read_jsonl(_run_dir(run_id, run_store) / "events.jsonl")


def _latest_metrics_by_name(metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for metric in metrics:
        name = metric.get("name")
        if isinstance(name, str):
            latest[name] = metric
    return latest


def _is_numeric_metric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
        """body{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;color:#17202a;background:#f7f8fa}main{max-width:1120px;margin:0 auto;padding:32px 20px}h1,h2{color:#101820}a{color:#0b5cad}table{border-collapse:collapse;width:100%;margin:16px 0;background:#fff}th,td{border:1px solid #d7dce2;padding:8px 10px;text-align:left;vertical-align:top}th{background:#edf1f5}.panel{background:#fff;border:1px solid #d7dce2;padding:16px;margin:16px 0}.safe{color:#116329;font-weight:600}.false{color:#5f6b7a}.unsafe{color:#a61b1b;font-weight:700}.meta{color:#52606d}code{background:#eef2f6;padding:2px 4px}""",
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


def _index_html(summaries: list[dict[str, Any]]) -> str:
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
        "<table><thead><tr>"
        "<th>Run</th><th>Project</th><th>Campaign</th><th>Run Type</th><th>Status</th>"
        "<th>Created</th><th>Finished</th><th>Source</th><th>Target</th><th>Artifacts</th><th>Metrics</th>"
        "</tr></thead><tbody>\n"
        f"{rows}\n"
        "</tbody></table>"
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
) -> str:
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
        "<h2>Metrics</h2><table><thead><tr><th>Name</th><th>Value</th><th>Step</th><th>Created</th></tr></thead><tbody>"
        + metric_rows
        + "</tbody></table>\n"
        "<h2>Artifacts</h2><table><thead><tr><th>Name</th><th>Type</th><th>Path</th><th>SHA-256</th><th>Metadata</th></tr></thead><tbody>"
        + artifact_rows
        + "</tbody></table>\n"
        "<h2>Events</h2><table><thead><tr><th>Type</th><th>Created</th><th>Message</th><th>Metadata</th></tr></thead><tbody>"
        + event_rows
        + "</tbody></table>\n"
    )
    return _page(f"OpenPlazma Run {run['runId']}", body, "../assets/observatory.css")


def _compare_file_name(run_a_id: str, run_b_id: str) -> str:
    if not _RUN_ID_RE.fullmatch(run_a_id) or not _RUN_ID_RE.fullmatch(run_b_id):
        raise ValueError("Compare run IDs must look like OPR-YYYYMMDD-000001.")
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
    summaries = summarize_runstore(run_store=run_store)
    selected_output = Path(output_dir) if output_dir is not None else _run_store_root(run_store) / "observatory"
    selected_output.mkdir(parents=True, exist_ok=True)
    _write_css(selected_output)

    index_path = selected_output / "index.html"
    _ensure_inside(selected_output, index_path)
    index_path.write_text(_index_html(summaries), encoding="utf-8")

    runs_dir = selected_output / "runs"
    _ensure_inside(selected_output, runs_dir)
    if runs_dir.exists():
        shutil.rmtree(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)

    compare_dir = selected_output / "compare"
    _ensure_inside(selected_output, compare_dir)
    if compare_dir.exists():
        shutil.rmtree(compare_dir)

    for summary in summaries:
        run_id = summary["runId"]
        run = _load_observatory_run(run_id, run_store=run_store)
        metrics = load_metrics(run_id, run_store=run_store)
        artifacts = load_run_artifacts(run_id, run_store=run_store)
        events = load_run_events(run_id, run_store=run_store)
        run_page = runs_dir / f"{run_id}.html"
        _ensure_inside(selected_output, run_page)
        run_page.write_text(_run_detail_html(run, metrics, artifacts, events), encoding="utf-8")

    return selected_output


def export_observatory_compare_html(
    run_a_id: str,
    run_b_id: str,
    run_store: str | Path = ".openplazma",
    output_dir: str | Path | None = None,
) -> Path:
    selected_output = export_observatory_html(run_store=run_store, output_dir=output_dir)
    compare_dir = selected_output / "compare"
    _ensure_inside(selected_output, compare_dir)
    compare_dir.mkdir(parents=True, exist_ok=True)

    comparison = compare_runs(run_a_id, run_b_id, run_store=run_store)
    compare_path = compare_dir / _compare_file_name(run_a_id, run_b_id)
    _ensure_inside(compare_dir, compare_path)
    compare_path.write_text(_compare_html(comparison), encoding="utf-8")
    return compare_path
