from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._json import load_json, save_json
from ._validation import require_keys, require_mapping, require_string
from .context import validate_experiment_context

SAFE_CAPABILITIES = {
    "readData": True,
    "writeArtifacts": True,
    "runSimulation": False,
    "submitComputeJob": False,
    "readFacilityTelemetry": False,
    "controlFacility": False,
}

DEFAULT_LIMITATIONS = [
    "STATIC_FIXTURE data only.",
    "Not a validated fusion simulator.",
    "Not a reactor design tool.",
    "Not a real hardware control system.",
]

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _safe_capabilities(capabilities: dict[str, Any] | None = None) -> dict[str, bool]:
    selected = dict(SAFE_CAPABILITIES)
    if capabilities is not None:
        require_keys(capabilities, list(SAFE_CAPABILITIES), "RunRecord.capabilities")
        selected.update(capabilities)

    for field, expected in SAFE_CAPABILITIES.items():
        if selected.get(field) is not expected:
            raise ValueError(f"RunRecord.capabilities.{field} must be {str(expected).lower()}.")
    return selected


def _require_static_fixture_source(source: dict[str, Any]) -> dict[str, Any]:
    require_keys(source, ["provider", "sourceLabel"], "RunRecord.source")
    if source["provider"] != "STATIC_FIXTURE":
        raise ValueError("RunRecord.source.provider must be STATIC_FIXTURE.")
    require_string(source["sourceLabel"], "RunRecord.source.sourceLabel")
    result = {
        "provider": source["provider"],
        "sourceLabel": source["sourceLabel"],
    }
    if source.get("inspiredBy") is not None:
        if source["inspiredBy"] != "FAIR_MAST":
            raise ValueError("RunRecord.source.inspiredBy must be FAIR_MAST when provided.")
        result["inspiredBy"] = "FAIR_MAST"
    return result


def _default_source(context: dict[str, Any] | None) -> dict[str, Any]:
    if context is not None:
        validate_experiment_context(context)
        return _require_static_fixture_source(require_mapping(context["source"], "ExperimentContext.source"))
    return {
        "provider": "STATIC_FIXTURE",
        "sourceLabel": "Local OpenPlazma RunStore",
    }


def _run_store_root(run_store: str | Path) -> Path:
    return Path(run_store)


def _runs_root(run_store: str | Path) -> Path:
    return _run_store_root(run_store) / "runs"


def _next_run_id(run_store: str | Path) -> str:
    runs_root = _runs_root(run_store)
    runs_root.mkdir(parents=True, exist_ok=True)
    prefix = f"OPR-{_today()}-"
    existing = []
    for path in runs_root.glob(f"{prefix}*"):
        suffix = path.name.removeprefix(prefix)
        if suffix.isdigit():
            existing.append(int(suffix))
    return f"{prefix}{(max(existing, default=0) + 1):06d}"


def _run_dir(run_id: str, run_store: str | Path) -> Path:
    if not re.fullmatch(r"OPR-\d{8}-\d{6}", run_id):
        raise ValueError("run_id must look like OPR-YYYYMMDD-000001.")
    return _runs_root(run_store) / run_id


def _write_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        json.dump(value, file, separators=(",", ":"), ensure_ascii=False)
        file.write("\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"Expected JSON object line in {path}.")
                values.append(value)
    return values


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_artifact_filename(name: str) -> str:
    require_string(name, "ArtifactRecord.name")
    if not _SAFE_NAME_RE.fullmatch(name) or name in {".", ".."}:
        raise ValueError("ArtifactRecord.name may only contain letters, numbers, dots, underscores, and hyphens.")
    return f"{name.replace('_', '-')}.json"


def _ensure_inside(parent: Path, child: Path) -> None:
    parent_resolved = parent.resolve()
    child_resolved = child.resolve()
    if parent_resolved != child_resolved and parent_resolved not in child_resolved.parents:
        raise ValueError("Artifact path must remain inside the run directory.")


def _validate_metric_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("MetricRecord.value must be finite when it is a number.")
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        json.dumps(value)
    except TypeError as error:
        raise ValueError("MetricRecord.value must be JSON-serializable.") from error
    return value


def _validate_run_record(record: dict[str, Any]) -> dict[str, Any]:
    require_keys(
        record,
        [
            "kind",
            "version",
            "runId",
            "project",
            "campaign",
            "runType",
            "status",
            "createdAt",
            "updatedAt",
            "target",
            "source",
            "capabilities",
            "contextRef",
            "artifactCount",
            "metricCount",
            "limitations",
        ],
        "RunRecord",
    )
    if record["kind"] != "openplazma.run":
        raise ValueError("RunRecord.kind must be openplazma.run.")
    if record["version"] != "0.1.0":
        raise ValueError("RunRecord.version must be 0.1.0.")
    if record["status"] not in {"running", "finished", "failed"}:
        raise ValueError("RunRecord.status must be running, finished, or failed.")
    require_string(record["runId"], "RunRecord.runId")
    require_string(record["project"], "RunRecord.project")
    require_string(record["campaign"], "RunRecord.campaign")
    require_string(record["runType"], "RunRecord.runType")
    target = require_mapping(record["target"], "RunRecord.target")
    require_keys(target, ["type", "id", "label"], "RunRecord.target")
    if target["type"] != "local_run_store":
        raise ValueError("RunRecord.target.type must be local_run_store.")
    _require_static_fixture_source(require_mapping(record["source"], "RunRecord.source"))
    _safe_capabilities(require_mapping(record["capabilities"], "RunRecord.capabilities"))
    return record


class Run:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.artifacts_dir = run_dir / "artifacts"
        self.run_json_path = run_dir / "run.json"
        self.manifest_path = run_dir / "manifest.json"
        self.metrics_path = run_dir / "metrics.jsonl"
        self.events_path = run_dir / "events.jsonl"

    @property
    def run_id(self) -> str:
        return self.run_record["runId"]

    @property
    def run_record(self) -> dict[str, Any]:
        return load_json(self.run_json_path)

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.finish()
        else:
            self.fail(str(exc) if exc else "Run failed.")

    def _save_run_record(self, record: dict[str, Any]) -> None:
        save_json(_validate_run_record(record), self.run_json_path)

    def _manifest(self) -> dict[str, Any]:
        return load_json(self.manifest_path)

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        save_json(manifest, self.manifest_path)

    def _event(self, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        record = {
            "kind": "openplazma.event",
            "version": "0.1.0",
            "runId": self.run_id,
            "eventType": event_type,
            "createdAt": _now(),
            "message": message,
            "metadata": metadata or {},
        }
        _write_jsonl(self.events_path, record)

    def log_metric(self, name: str, value: Any, step: int | None = None) -> dict[str, Any]:
        require_string(name, "MetricRecord.name")
        if step is not None and (not isinstance(step, int) or isinstance(step, bool) or step < 0):
            raise ValueError("MetricRecord.step must be a non-negative integer when provided.")
        record = {
            "kind": "openplazma.metric",
            "version": "0.1.0",
            "runId": self.run_id,
            "name": name,
            "value": _validate_metric_value(value),
            "step": step,
            "createdAt": _now(),
        }
        _write_jsonl(self.metrics_path, record)

        run_record = self.run_record
        run_record["metricCount"] = int(run_record.get("metricCount", 0)) + 1
        run_record["updatedAt"] = record["createdAt"]
        self._save_run_record(run_record)
        self._event("metric_logged", f"Logged metric {name}", {"name": name})
        return record

    def log_artifact(
        self,
        name: str,
        artifact_type: str,
        data: dict[str, Any] | str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        require_string(artifact_type, "ArtifactRecord.type")
        filename = _safe_artifact_filename(name)
        artifact_path = self.artifacts_dir / filename
        _ensure_inside(self.run_dir, artifact_path)
        if artifact_path.exists():
            raise ValueError(f"Artifact '{name}' already exists for run {self.run_id}.")

        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(data, dict):
            save_json(data, artifact_path)
        elif isinstance(data, (str, Path)):
            source_path = Path(data)
            if not source_path.is_file():
                raise ValueError("Artifact source path must be an existing file.")
            shutil.copyfile(source_path, artifact_path)
        else:
            raise ValueError("Artifact data must be a JSON object or file path.")

        manifest = self._manifest()
        artifact_count = len(manifest.get("artifacts", [])) + 1
        artifact_id = f"OPA-{_today()}-{artifact_count:06d}"
        created_at = _now()
        record = {
            "kind": "openplazma.artifact",
            "version": "0.1.0",
            "artifactId": artifact_id,
            "runId": self.run_id,
            "name": name,
            "type": artifact_type,
            "path": artifact_path.relative_to(self.run_dir).as_posix(),
            "sha256": _sha256(artifact_path),
            "createdAt": created_at,
            "metadata": metadata or {},
        }
        manifest["artifacts"].append(record)
        manifest["updatedAt"] = created_at
        self._save_manifest(manifest)

        run_record = self.run_record
        run_record["artifactCount"] = artifact_count
        if artifact_type == "experiment_context":
            run_record["contextRef"] = {
                "artifactName": name,
                "artifactType": artifact_type,
            }
        run_record["updatedAt"] = created_at
        self._save_run_record(run_record)
        self._event("artifact_logged", f"Logged artifact {name}", {"artifactId": artifact_id})
        return record

    def finish(self) -> dict[str, Any]:
        record = self.run_record
        if record["status"] == "finished":
            return record
        finished_at = _now()
        record["status"] = "finished"
        record["updatedAt"] = finished_at
        record["finishedAt"] = finished_at
        self._save_run_record(record)
        self._event("run_finished", "Run finished.")
        return record

    def fail(self, message: str = "Run failed.") -> dict[str, Any]:
        record = self.run_record
        failed_at = _now()
        record["status"] = "failed"
        record["updatedAt"] = failed_at
        record["finishedAt"] = failed_at
        self._save_run_record(record)
        self._event("run_failed", message)
        return record


def start_run(
    *,
    project: str,
    campaign: str,
    run_type: str,
    context: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    run_store: str | Path = ".openplazma",
    capabilities: dict[str, Any] | None = None,
) -> Run:
    require_string(project, "RunRecord.project")
    require_string(campaign, "RunRecord.campaign")
    require_string(run_type, "RunRecord.runType")

    run_id = _next_run_id(run_store)
    root = _run_store_root(run_store)
    run_dir = _run_dir(run_id, run_store)
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "metrics.jsonl").touch()
    (run_dir / "events.jsonl").touch()

    created_at = _now()
    source = _default_source(context)
    context_limitations = context.get("limitations") if context else None
    limitations = context_limitations if isinstance(context_limitations, list) and context_limitations else DEFAULT_LIMITATIONS
    safe_capabilities = _safe_capabilities(capabilities or (context.get("capabilities") if context else None))

    run_record = {
        "kind": "openplazma.run",
        "version": "0.1.0",
        "runId": run_id,
        "project": project,
        "campaign": campaign,
        "runType": run_type,
        "status": "running",
        "createdAt": created_at,
        "updatedAt": created_at,
        "finishedAt": None,
        "target": {
            "type": "local_run_store",
            "id": str(root),
            "label": "Local OpenPlazma RunStore",
        },
        "source": source,
        "capabilities": safe_capabilities,
        "contextRef": None,
        "artifactCount": 0,
        "metricCount": 0,
        "limitations": limitations,
    }
    save_json(_validate_run_record(run_record), run_dir / "run.json")
    save_json(config or {}, run_dir / "config.json")
    save_json(
        {
            "kind": "openplazma.run_manifest",
            "version": "0.1.0",
            "runId": run_id,
            "createdAt": created_at,
            "updatedAt": created_at,
            "artifacts": [],
        },
        run_dir / "manifest.json",
    )

    run = Run(run_dir)
    run._event("run_started", "Run started.")
    return run


def list_runs(run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    runs_root = _runs_root(run_store)
    if not runs_root.exists():
        return []
    records = []
    for path in sorted(runs_root.iterdir()):
        if path.is_dir() and (path / "run.json").is_file():
            records.append(load_run(path.name, run_store))
    return records


def load_run(run_id: str, run_store: str | Path = ".openplazma") -> dict[str, Any]:
    return _validate_run_record(load_json(_run_dir(run_id, run_store) / "run.json"))


def load_metrics(run_id: str, run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    return _read_jsonl(_run_dir(run_id, run_store) / "metrics.jsonl")


def load_manifest(run_id: str, run_store: str | Path = ".openplazma") -> dict[str, Any]:
    return load_json(_run_dir(run_id, run_store) / "manifest.json")
