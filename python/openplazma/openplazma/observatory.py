from __future__ import annotations

import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any

from .runstore import load_manifest, load_metrics, load_run

_RUN_ID_RE = re.compile(r"^OPR-\d{8}-\d{6}$")


def _run_store_root(run_store: str | Path) -> Path:
    return Path(run_store)


def _runs_root(run_store: str | Path) -> Path:
    return _run_store_root(run_store) / "runs"


def _run_dir(run_id: str, run_store: str | Path) -> Path:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must look like OPR-YYYYMMDD-000001.")
    return _runs_root(run_store) / run_id


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


def summarize_run(run_id: str, run_store: str | Path = ".openplazma") -> dict[str, Any]:
    run = load_run(run_id, run_store=run_store)
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


def _write_css(output_dir: Path) -> None:
    css_path = output_dir / "assets" / "observatory.css"
    _ensure_inside(output_dir, css_path)
    css_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.write_text(
        """body{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;color:#17202a;background:#f7f8fa}main{max-width:1120px;margin:0 auto;padding:32px 20px}h1,h2{color:#101820}a{color:#0b5cad}table{border-collapse:collapse;width:100%;margin:16px 0;background:#fff}th,td{border:1px solid #d7dce2;padding:8px 10px;text-align:left;vertical-align:top}th{background:#edf1f5}.panel{background:#fff;border:1px solid #d7dce2;padding:16px;margin:16px 0}.safe{color:#116329;font-weight:600}.false{color:#5f6b7a}.meta{color:#52606d}code{background:#eef2f6;padding:2px 4px}""",
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
        f"<tr><th>{_html(key)}</th><td class=\"{'safe' if value is True else 'false'}\">{_html(value)}</td></tr>"
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

    for summary in summaries:
        run_id = summary["runId"]
        run = load_run(run_id, run_store=run_store)
        metrics = load_metrics(run_id, run_store=run_store)
        artifacts = load_run_artifacts(run_id, run_store=run_store)
        events = load_run_events(run_id, run_store=run_store)
        run_page = runs_dir / f"{run_id}.html"
        _ensure_inside(selected_output, run_page)
        run_page.write_text(_run_detail_html(run, metrics, artifacts, events), encoding="utf-8")

    return selected_output
