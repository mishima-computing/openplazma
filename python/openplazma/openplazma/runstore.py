from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._json import load_json, loads_json, save_json
from ._validation import require_iso_datetime, require_keys, require_list, require_mapping, require_string
from .context import validate_experiment_context
from .records import validate_study_record
from .signals import validate_signal_series
from .sources import validate_source_ref

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
    "Read-only analysis and decision support.",
    "No command/control path or hazardous operating procedure.",
    "Not a standalone authority for safety-critical operation or reactor design decisions.",
]

MAX_METRICS_PER_RUN = 100_000
MAX_ARTIFACTS_PER_RUN = 10_000
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_RUN_ID_RE = re.compile(r"^OPR-\d{8}-\d{6}$")
_ARTIFACT_ID_RE = re.compile(r"^OPA-\d{8}-\d{6}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_WRITE_LOCK_POLL_SECONDS = 0.01
_WRITE_LOCK_TIMEOUT_SECONDS = 10.0
_STALE_LOCK_GRACE_SECONDS = 30.0
_LOCK_STATE = threading.local()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _parse_required_datetime(value: Any, name: str) -> datetime:
    timestamp = require_iso_datetime(value, name)
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _require_at_or_after(actual: datetime, minimum: datetime, actual_name: str, minimum_name: str) -> None:
    if actual < minimum:
        raise ValueError(f"{actual_name} must be at or after {minimum_name}.")


def _safe_capabilities(capabilities: dict[str, Any] | None = None) -> dict[str, bool]:
    selected = dict(SAFE_CAPABILITIES)
    if capabilities is not None:
        require_keys(capabilities, list(SAFE_CAPABILITIES), "RunRecord.capabilities")
        selected.update(capabilities)

    for field, expected in SAFE_CAPABILITIES.items():
        if selected.get(field) is not expected:
            raise ValueError(f"RunRecord.capabilities.{field} must be {str(expected).lower()}.")
    return selected


def _require_readonly_source(source: dict[str, Any]) -> dict[str, Any]:
    require_keys(source, ["provider", "sourceLabel"], "RunRecord.source")
    validate_source_ref(source, "RunRecord.source")
    result = {
        "provider": source["provider"],
        "sourceLabel": source["sourceLabel"],
    }
    for field in ["inspiredBy", "uri", "sha256", "validationStatus"]:
        if source.get(field) is not None:
            result[field] = source[field]
    return result


def _default_source(context: dict[str, Any] | None) -> dict[str, Any]:
    if context is not None:
        validate_experiment_context(context)
        return _require_readonly_source(require_mapping(context["source"], "ExperimentContext.source"))
    return {
        "provider": "STATIC_FIXTURE",
        "sourceLabel": "Local OpenPlazma RunStore",
    }


def _run_store_root(run_store: str | Path) -> Path:
    return Path(run_store)


def _runs_root(run_store: str | Path) -> Path:
    return _run_store_root(run_store) / "runs"


class _RunStoreWriteLock:
    def __init__(
        self,
        run_store: str | Path,
        *,
        timeout_seconds: float = _WRITE_LOCK_TIMEOUT_SECONDS,
        stale_grace_seconds: float = _STALE_LOCK_GRACE_SECONDS,
    ) -> None:
        self.root = _run_store_root(run_store)
        self.lock_dir = self.root / ".write.lock"
        self.timeout_seconds = timeout_seconds
        self.stale_grace_seconds = stale_grace_seconds
        self.acquired = False
        self.lock_key = ""
        self.reentrant = False

    def __enter__(self) -> "_RunStoreWriteLock":
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock_key = self.root.resolve().as_posix()
        lock_counts = _thread_lock_counts()
        depth = lock_counts.get(self.lock_key, 0)
        if depth > 0:
            lock_counts[self.lock_key] = depth + 1
            self.reentrant = True
            return self

        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self.lock_dir.mkdir()
                self.acquired = True
                lock_counts[self.lock_key] = 1
                (self.lock_dir / "owner").write_text(f"pid={os.getpid()}\n", encoding="utf-8")
                return self
            except FileExistsError:
                if self._clear_stale_lock():
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for RunStore write lock: {self.lock_dir}.")
                time.sleep(_WRITE_LOCK_POLL_SECONDS)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        lock_counts = _thread_lock_counts()
        depth = lock_counts.get(self.lock_key, 0)
        if self.reentrant or depth > 1:
            if depth <= 1:
                lock_counts.pop(self.lock_key, None)
            else:
                lock_counts[self.lock_key] = depth - 1
            return

        if not self.acquired:
            return
        try:
            (self.lock_dir / "owner").unlink()
        except FileNotFoundError:
            pass
        self.lock_dir.rmdir()
        lock_counts.pop(self.lock_key, None)
        self.acquired = False

    def _clear_stale_lock(self) -> bool:
        owner_state = self._lock_owner_state()
        if owner_state == "dead":
            shutil.rmtree(self.lock_dir, ignore_errors=True)
            return True
        if owner_state == "malformed" and self._lock_is_older_than_grace_period():
            shutil.rmtree(self.lock_dir, ignore_errors=True)
            return True
        return False

    def _lock_owner_state(self) -> str:
        owner_path = self.lock_dir / "owner"
        try:
            owner = owner_path.read_text(encoding="utf-8")
        except OSError:
            return "malformed"
        match = re.search(r"^pid=(\d+)$", owner, re.MULTILINE)
        if match is None:
            return "malformed"
        pid = int(match.group(1))
        if pid <= 0:
            return "dead"
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return "dead"
        except PermissionError:
            return "live"
        return "live"

    def _lock_is_older_than_grace_period(self) -> bool:
        try:
            lock_age = time.time() - self.lock_dir.stat().st_mtime
        except OSError:
            return False
        return lock_age > self.stale_grace_seconds


def _thread_lock_counts() -> dict[str, int]:
    counts = getattr(_LOCK_STATE, "counts", None)
    if counts is None:
        counts = {}
        _LOCK_STATE.counts = counts
    return counts


def _run_store_write_lock(run_store: str | Path) -> _RunStoreWriteLock:
    return _RunStoreWriteLock(run_store)


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
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must look like OPR-YYYYMMDD-000001.")
    return _runs_root(run_store) / run_id


def _allocate_run_dir(run_store: str | Path) -> tuple[str, Path]:
    last_error: FileExistsError | None = None
    for _ in range(20):
        run_id = _next_run_id(run_store)
        run_dir = _run_dir(run_id, run_store)
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            return run_id, run_dir
        except FileExistsError as error:
            last_error = error
    raise RuntimeError("Could not allocate a unique run id.") from last_error


def _write_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        line = json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except TypeError as error:
        raise ValueError("JSONL value must be serializable.") from error
    except ValueError as error:
        raise ValueError("JSONL value must not contain NaN or Infinity.") from error
    with path.open("a", encoding="utf-8") as file:
        file.write(line)
        file.write("\n")


def _require_record_count_within_limit(count: int, limit: int, limit_name: str, record_name: str) -> None:
    if count > limit:
        raise ValueError(f"{record_name} count exceeds {limit_name} ({limit}).")


def _require_artifact_size_within_limit(path: Path) -> None:
    size = path.stat().st_size
    if size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"Artifact file size exceeds MAX_ARTIFACT_BYTES ({MAX_ARTIFACT_BYTES}).")


def _snapshot_files(paths: list[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def _restore_files(snapshot: dict[Path, bytes | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.stat().st_size > 0 and not path.read_bytes().endswith(b"\n"):
        raise ValueError(f"JSONL file must end with a newline: {path}.")
    values: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if line:
                try:
                    value = loads_json(line)
                except ValueError as error:
                    raise ValueError(f"Invalid JSONL record in {path} at line {line_number}: {error}") from error
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


def _require_int(value: Any, name: str, *, nonnegative: bool = False) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer.")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be nonnegative.")
    return value


def _require_string_list(value: Any, name: str, *, min_items: int = 0) -> list[Any]:
    items = require_list(value, name)
    if len(items) < min_items:
        raise ValueError(f"{name} must include at least {min_items} item(s).")
    for index, item in enumerate(items):
        require_string(item, f"{name}[{index}]")
    return items


def _validate_json_value(value: Any, name: str) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} must contain only finite numbers.")
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{name}[{index}]")
        return value
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{name} object keys must be strings.")
            _validate_json_value(item, f"{name}.{key}")
        return value
    raise ValueError(f"{name} must be a strict JSON value.")


def _validate_json_object(value: Any, name: str) -> dict[str, Any]:
    json_object = require_mapping(value, name)
    _validate_json_value(json_object, name)
    return json_object


def _validate_artifact_path(value: Any, name: str) -> str:
    artifact_path = require_string(value, name)
    parts = Path(artifact_path).parts
    if (
        Path(artifact_path).is_absolute()
        or not artifact_path.startswith("artifacts/")
        or "\\" in artifact_path
        or ".." in parts
        or any(":" in part for part in parts)
    ):
        raise ValueError(f"Artifact path must remain under artifacts/ ({name}).")
    return artifact_path


def _validate_metric_value(value: Any) -> Any:
    return _validate_json_value(value, "MetricRecord.value")


def _validate_context_ref(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    context_ref = require_mapping(value, "RunRecord.contextRef")
    require_keys(context_ref, ["artifactName", "artifactType"], "RunRecord.contextRef")
    require_string(context_ref["artifactName"], "RunRecord.contextRef.artifactName")
    require_string(context_ref["artifactType"], "RunRecord.contextRef.artifactType")
    return context_ref


def _validate_run_record(record: dict[str, Any], *, expected_run_id: str | None = None) -> dict[str, Any]:
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
    run_id = require_string(record["runId"], "RunRecord.runId")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("RunRecord.runId must look like OPR-YYYYMMDD-000001.")
    if expected_run_id is not None and run_id != expected_run_id:
        raise ValueError("RunRecord.runId must match the requested run_id.")
    if record["status"] not in {"running", "finished", "failed"}:
        raise ValueError("RunRecord.status must be running, finished, or failed.")
    if record["status"] == "running" and record.get("finishedAt") is not None:
        raise ValueError("RunRecord.finishedAt must be null while status is running.")
    if record["status"] in {"finished", "failed"} and record.get("finishedAt") is None:
        raise ValueError("RunRecord.finishedAt is required when status is finished or failed.")
    require_string(record["project"], "RunRecord.project")
    require_string(record["campaign"], "RunRecord.campaign")
    require_string(record["runType"], "RunRecord.runType")
    created_at = _parse_required_datetime(record["createdAt"], "RunRecord.createdAt")
    updated_at = _parse_required_datetime(record["updatedAt"], "RunRecord.updatedAt")
    _require_at_or_after(updated_at, created_at, "RunRecord.updatedAt", "RunRecord.createdAt")
    if record.get("finishedAt") is not None:
        finished_at = _parse_required_datetime(record["finishedAt"], "RunRecord.finishedAt")
        _require_at_or_after(finished_at, updated_at, "RunRecord.finishedAt", "RunRecord.updatedAt")
    target = require_mapping(record["target"], "RunRecord.target")
    require_keys(target, ["type", "id", "label"], "RunRecord.target")
    if target["type"] != "local_run_store":
        raise ValueError("RunRecord.target.type must be local_run_store.")
    require_string(target["id"], "RunRecord.target.id")
    require_string(target["label"], "RunRecord.target.label")
    _require_readonly_source(require_mapping(record["source"], "RunRecord.source"))
    _safe_capabilities(require_mapping(record["capabilities"], "RunRecord.capabilities"))
    _validate_context_ref(record["contextRef"])
    _require_int(record["artifactCount"], "RunRecord.artifactCount", nonnegative=True)
    _require_int(record["metricCount"], "RunRecord.metricCount", nonnegative=True)
    _require_string_list(record["limitations"], "RunRecord.limitations", min_items=1)
    return record


def _validate_metric_record(record: dict[str, Any], *, expected_run_id: str | None = None) -> dict[str, Any]:
    require_keys(record, ["kind", "version", "runId", "name", "value", "createdAt"], "MetricRecord")
    if record["kind"] != "openplazma.metric":
        raise ValueError("MetricRecord.kind must be openplazma.metric.")
    if record["version"] != "0.1.0":
        raise ValueError("MetricRecord.version must be 0.1.0.")
    run_id = require_string(record["runId"], "MetricRecord.runId")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("MetricRecord.runId must look like OPR-YYYYMMDD-000001.")
    if expected_run_id is not None and run_id != expected_run_id:
        raise ValueError("MetricRecord.runId must match the requested run_id.")
    require_string(record["name"], "MetricRecord.name")
    _validate_metric_value(record["value"])
    if record.get("step") is not None:
        _require_int(record["step"], "MetricRecord.step", nonnegative=True)
    require_iso_datetime(record["createdAt"], "MetricRecord.createdAt")
    return record


def _validate_artifact_record(record: dict[str, Any], *, expected_run_id: str | None = None) -> dict[str, Any]:
    require_keys(
        record,
        ["kind", "version", "artifactId", "runId", "name", "type", "path", "sha256", "createdAt", "metadata"],
        "ArtifactRecord",
    )
    if record["kind"] != "openplazma.artifact":
        raise ValueError("ArtifactRecord.kind must be openplazma.artifact.")
    if record["version"] != "0.1.0":
        raise ValueError("ArtifactRecord.version must be 0.1.0.")
    artifact_id = require_string(record["artifactId"], "ArtifactRecord.artifactId")
    if not _ARTIFACT_ID_RE.fullmatch(artifact_id):
        raise ValueError("ArtifactRecord.artifactId must look like OPA-YYYYMMDD-000001.")
    run_id = require_string(record["runId"], "ArtifactRecord.runId")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("ArtifactRecord.runId must look like OPR-YYYYMMDD-000001.")
    if expected_run_id is not None and run_id != expected_run_id:
        raise ValueError("ArtifactRecord.runId must match the requested run_id.")
    require_string(record["name"], "ArtifactRecord.name")
    require_string(record["type"], "ArtifactRecord.type")
    _validate_artifact_path(record["path"], "ArtifactRecord.path")
    digest = require_string(record["sha256"], "ArtifactRecord.sha256")
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError("ArtifactRecord.sha256 must be a lowercase SHA-256 hex digest.")
    require_iso_datetime(record["createdAt"], "ArtifactRecord.createdAt")
    _validate_json_object(record["metadata"], "ArtifactRecord.metadata")
    return record


def _validate_event_record(record: dict[str, Any], *, expected_run_id: str | None = None) -> dict[str, Any]:
    require_keys(record, ["kind", "version", "runId", "eventType", "createdAt", "message", "metadata"], "EventRecord")
    if record["kind"] != "openplazma.event":
        raise ValueError("EventRecord.kind must be openplazma.event.")
    if record["version"] != "0.1.0":
        raise ValueError("EventRecord.version must be 0.1.0.")
    run_id = require_string(record["runId"], "EventRecord.runId")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("EventRecord.runId must look like OPR-YYYYMMDD-000001.")
    if expected_run_id is not None and run_id != expected_run_id:
        raise ValueError("EventRecord.runId must match the requested run_id.")
    if record["eventType"] not in {"run_started", "metric_logged", "artifact_logged", "run_finished", "run_failed"}:
        raise ValueError("EventRecord.eventType is not supported.")
    require_iso_datetime(record["createdAt"], "EventRecord.createdAt")
    require_string(record["message"], "EventRecord.message")
    _validate_json_object(record["metadata"], "EventRecord.metadata")
    return record


def _validate_run_manifest(manifest: dict[str, Any], *, expected_run_id: str | None = None) -> dict[str, Any]:
    require_keys(manifest, ["kind", "version", "runId", "createdAt", "updatedAt", "artifacts"], "RunManifest")
    if manifest["kind"] != "openplazma.run_manifest":
        raise ValueError("RunManifest.kind must be openplazma.run_manifest.")
    if manifest["version"] != "0.1.0":
        raise ValueError("RunManifest.version must be 0.1.0.")
    run_id = require_string(manifest["runId"], "RunManifest.runId")
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("RunManifest.runId must look like OPR-YYYYMMDD-000001.")
    if expected_run_id is not None and run_id != expected_run_id:
        raise ValueError("RunManifest.runId must match the requested run_id.")
    created_at = _parse_required_datetime(manifest["createdAt"], "RunManifest.createdAt")
    updated_at = _parse_required_datetime(manifest["updatedAt"], "RunManifest.updatedAt")
    _require_at_or_after(updated_at, created_at, "RunManifest.updatedAt", "RunManifest.createdAt")
    artifact_ids: set[str] = set()
    artifact_paths: set[str] = set()
    artifacts = require_list(manifest["artifacts"], "RunManifest.artifacts")
    _require_record_count_within_limit(len(artifacts), MAX_ARTIFACTS_PER_RUN, "MAX_ARTIFACTS_PER_RUN", "ArtifactRecord")
    for index, artifact_ref in enumerate(artifacts):
        artifact = require_mapping(artifact_ref, f"RunManifest.artifacts[{index}]")
        _validate_artifact_record(artifact, expected_run_id=run_id)
        artifact_created_at = _parse_required_datetime(artifact["createdAt"], "ArtifactRecord.createdAt")
        _require_at_or_after(artifact_created_at, created_at, "ArtifactRecord.createdAt", "RunManifest.createdAt")
        _require_at_or_after(updated_at, artifact_created_at, "RunManifest.updatedAt", "ArtifactRecord.createdAt")
        if artifact["artifactId"] in artifact_ids:
            raise ValueError(f"duplicate artifact id '{artifact['artifactId']}' in RunManifest.")
        if artifact["path"] in artifact_paths:
            raise ValueError(f"duplicate artifact path '{artifact['path']}' in RunManifest.")
        artifact_ids.add(artifact["artifactId"])
        artifact_paths.add(artifact["path"])
    return manifest


def _artifact_file_path(run_dir: Path, artifact: dict[str, Any]) -> Path:
    artifact_path = run_dir / artifact["path"]
    _ensure_inside(run_dir / "artifacts", artifact_path)
    return artifact_path


def _validate_run_manifest_artifact_files(manifest: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    for artifact in manifest["artifacts"]:
        artifact_path = _artifact_file_path(run_dir, artifact)
        if not artifact_path.is_file():
            raise ValueError(f"Artifact file is missing: {artifact['path']}.")
        _require_artifact_size_within_limit(artifact_path)
        if _sha256(artifact_path) != artifact["sha256"]:
            raise ValueError("ArtifactRecord.sha256 must match the artifact file digest.")
    return manifest


def _validate_event_sequence(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        raise ValueError("EventRecord sequence must start with run_started.")
    if events[0]["eventType"] != "run_started":
        raise ValueError("EventRecord sequence must start with run_started.")
    if sum(1 for event in events if event["eventType"] == "run_started") != 1:
        raise ValueError("EventRecord sequence must include exactly one run_started event.")
    previous_created_at = _parse_required_datetime(events[0]["createdAt"], "EventRecord.createdAt")
    for event in events[1:]:
        created_at = _parse_required_datetime(event["createdAt"], "EventRecord.createdAt")
        _require_at_or_after(created_at, previous_created_at, "EventRecord.createdAt", "previous EventRecord.createdAt")
        previous_created_at = created_at
    terminal_events = [event for event in events if event["eventType"] in {"run_finished", "run_failed"}]
    if len(terminal_events) > 1:
        raise ValueError("EventRecord sequence must include at most one terminal event.")
    if terminal_events and events[-1] is not terminal_events[0]:
        raise ValueError("EventRecord terminal event must be the last event.")
    return events


def _validate_run_store_consistency(
    record: dict[str, Any],
    *,
    manifest: dict[str, Any],
    metrics: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    run_created_at = _parse_required_datetime(record["createdAt"], "RunRecord.createdAt")
    manifest_created_at = _parse_required_datetime(manifest["createdAt"], "RunManifest.createdAt")
    _require_at_or_after(manifest_created_at, run_created_at, "RunManifest.createdAt", "RunRecord.createdAt")
    for metric in metrics:
        metric_created_at = _parse_required_datetime(metric["createdAt"], "MetricRecord.createdAt")
        _require_at_or_after(metric_created_at, run_created_at, "MetricRecord.createdAt", "RunRecord.createdAt")
    for artifact in manifest["artifacts"]:
        artifact_created_at = _parse_required_datetime(artifact["createdAt"], "ArtifactRecord.createdAt")
        _require_at_or_after(artifact_created_at, run_created_at, "ArtifactRecord.createdAt", "RunRecord.createdAt")
    for event in events:
        event_created_at = _parse_required_datetime(event["createdAt"], "EventRecord.createdAt")
        _require_at_or_after(event_created_at, run_created_at, "EventRecord.createdAt", "RunRecord.createdAt")

    _require_record_count_within_limit(len(metrics), MAX_METRICS_PER_RUN, "MAX_METRICS_PER_RUN", "MetricRecord")
    _require_record_count_within_limit(len(manifest["artifacts"]), MAX_ARTIFACTS_PER_RUN, "MAX_ARTIFACTS_PER_RUN", "ArtifactRecord")
    if record["artifactCount"] != len(manifest["artifacts"]):
        raise ValueError("RunRecord.artifactCount must match RunManifest artifact count.")
    if record["metricCount"] != len(metrics):
        raise ValueError("RunRecord.metricCount must match metrics.jsonl record count.")
    metric_event_count = sum(1 for event in events if event["eventType"] == "metric_logged")
    if metric_event_count != len(metrics):
        raise ValueError("EventRecord metric_logged count must match metrics.jsonl record count.")
    artifact_event_count = sum(1 for event in events if event["eventType"] == "artifact_logged")
    if artifact_event_count != len(manifest["artifacts"]):
        raise ValueError("EventRecord artifact_logged count must match RunManifest artifact count.")

    context_ref = record["contextRef"]
    if context_ref is not None:
        if not any(
            artifact["name"] == context_ref["artifactName"] and artifact["type"] == context_ref["artifactType"]
            for artifact in manifest["artifacts"]
        ):
            raise ValueError("RunRecord.contextRef must reference an artifact in RunManifest.")

    terminal_event_type = events[-1]["eventType"] if events[-1]["eventType"] in {"run_finished", "run_failed"} else None
    if record["status"] == "running" and terminal_event_type is not None:
        raise ValueError("RunRecord.status running must not have a terminal event.")
    if record["status"] == "finished" and terminal_event_type != "run_finished":
        raise ValueError("RunRecord.status finished requires a run_finished terminal event.")
    if record["status"] == "failed" and terminal_event_type != "run_failed":
        raise ValueError("RunRecord.status failed requires a run_failed terminal event.")
    if terminal_event_type is not None and record.get("finishedAt") is not None:
        terminal_event_created_at = _parse_required_datetime(events[-1]["createdAt"], "EventRecord.createdAt")
        finished_at = _parse_required_datetime(record["finishedAt"], "RunRecord.finishedAt")
        _require_at_or_after(terminal_event_created_at, finished_at, "EventRecord.createdAt", "RunRecord.finishedAt")
    return record


def _require_running_run(record: dict[str, Any]) -> None:
    if record["status"] != "running":
        raise ValueError("Run must be running before logging metrics or artifacts.")


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
        run_id = self.run_dir.name
        if not _RUN_ID_RE.fullmatch(run_id):
            raise ValueError("RunRecord.runId must look like OPR-YYYYMMDD-000001.")
        return run_id

    @property
    def run_record(self) -> dict[str, Any]:
        return load_run(self.run_id, run_store=self.run_dir.parent.parent)

    def __enter__(self) -> "Run":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.finish()
        else:
            self.fail(str(exc) if exc else "Run failed.")

    def _save_run_record(self, record: dict[str, Any]) -> None:
        save_json(_validate_run_record(record, expected_run_id=self.run_id), self.run_json_path)

    def _manifest(self) -> dict[str, Any]:
        manifest = _validate_run_manifest(load_json(self.manifest_path), expected_run_id=self.run_id)
        return _validate_run_manifest_artifact_files(manifest, self.run_dir)

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        validated = _validate_run_manifest(manifest, expected_run_id=self.run_id)
        save_json(_validate_run_manifest_artifact_files(validated, self.run_dir), self.manifest_path)

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
        _validate_event_record(record, expected_run_id=self.run_id)
        _write_jsonl(self.events_path, record)

    def log_metric(self, name: str, value: Any, step: int | None = None) -> dict[str, Any]:
        with _run_store_write_lock(self.run_dir.parent.parent):
            return self._log_metric_unlocked(name, value, step)

    def _log_metric_unlocked(self, name: str, value: Any, step: int | None = None) -> dict[str, Any]:
        require_string(name, "MetricRecord.name")
        if step is not None and (not isinstance(step, int) or isinstance(step, bool) or step < 0):
            raise ValueError("MetricRecord.step must be a non-negative integer when provided.")
        run_record = self.run_record
        _require_running_run(run_record)
        _require_record_count_within_limit(
            int(run_record.get("metricCount", 0)) + 1,
            MAX_METRICS_PER_RUN,
            "MAX_METRICS_PER_RUN",
            "MetricRecord",
        )
        record = {
            "kind": "openplazma.metric",
            "version": "0.1.0",
            "runId": self.run_id,
            "name": name,
            "value": _validate_metric_value(value),
            "step": step,
            "createdAt": _now(),
        }
        _validate_metric_record(record, expected_run_id=self.run_id)
        snapshot = _snapshot_files([self.metrics_path, self.run_json_path, self.events_path])
        try:
            _write_jsonl(self.metrics_path, record)
            run_record["metricCount"] = int(run_record.get("metricCount", 0)) + 1
            run_record["updatedAt"] = record["createdAt"]
            self._save_run_record(run_record)
            self._event("metric_logged", f"Logged metric {name}", {"name": name})
        except Exception:
            _restore_files(snapshot)
            raise
        return record

    def log_artifact(
        self,
        name: str,
        artifact_type: str,
        data: dict[str, Any] | str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with _run_store_write_lock(self.run_dir.parent.parent):
            return self._log_artifact_unlocked(name, artifact_type, data, metadata)

    def _log_artifact_unlocked(
        self,
        name: str,
        artifact_type: str,
        data: dict[str, Any] | str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        require_string(artifact_type, "ArtifactRecord.type")
        metadata_value = _validate_json_object(metadata or {}, "ArtifactRecord.metadata")
        filename = _safe_artifact_filename(name)
        artifact_path = self.artifacts_dir / filename
        _ensure_inside(self.run_dir, artifact_path)
        if artifact_path.exists():
            raise ValueError(f"Artifact '{name}' already exists for run {self.run_id}.")

        run_record = self.run_record
        _require_running_run(run_record)
        manifest = self._manifest()
        _require_record_count_within_limit(
            len(manifest.get("artifacts", [])) + 1,
            MAX_ARTIFACTS_PER_RUN,
            "MAX_ARTIFACTS_PER_RUN",
            "ArtifactRecord",
        )

        snapshot = _snapshot_files([artifact_path, self.manifest_path, self.run_json_path, self.events_path])
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        try:
            if isinstance(data, dict):
                save_json(_validate_json_object(data, "ArtifactRecord.data"), artifact_path)
            elif isinstance(data, (str, Path)):
                source_path = Path(data)
                if not source_path.is_file():
                    raise ValueError("Artifact source path must be an existing file.")
                _require_artifact_size_within_limit(source_path)
                shutil.copyfile(source_path, artifact_path)
            else:
                raise ValueError("Artifact data must be a JSON object or file path.")
            _require_artifact_size_within_limit(artifact_path)

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
                "metadata": metadata_value,
            }
            _validate_artifact_record(record, expected_run_id=self.run_id)
            manifest["artifacts"].append(record)
            manifest["updatedAt"] = created_at
            self._save_manifest(manifest)

            run_record["artifactCount"] = artifact_count
            if artifact_type == "experiment_context":
                run_record["contextRef"] = {
                    "artifactName": name,
                    "artifactType": artifact_type,
                }
            run_record["updatedAt"] = created_at
            self._save_run_record(run_record)
            self._event("artifact_logged", f"Logged artifact {name}", {"artifactId": artifact_id})
        except Exception:
            _restore_files(snapshot)
            raise
        return record

    def finish(self) -> dict[str, Any]:
        with _run_store_write_lock(self.run_dir.parent.parent):
            return self._finish_unlocked()

    def _finish_unlocked(self) -> dict[str, Any]:
        record = self.run_record
        if record["status"] == "finished":
            return record
        if record["status"] == "failed":
            raise ValueError("Run status is failed; failed runs cannot be finished.")
        finished_at = _now()
        record["status"] = "finished"
        record["updatedAt"] = finished_at
        record["finishedAt"] = finished_at
        snapshot = _snapshot_files([self.run_json_path, self.events_path])
        try:
            self._save_run_record(record)
            self._event("run_finished", "Run finished.")
        except Exception:
            _restore_files(snapshot)
            raise
        return record

    def fail(self, message: str = "Run failed.") -> dict[str, Any]:
        with _run_store_write_lock(self.run_dir.parent.parent):
            return self._fail_unlocked(message)

    def _fail_unlocked(self, message: str = "Run failed.") -> dict[str, Any]:
        record = self.run_record
        if record["status"] == "failed":
            return record
        if record["status"] == "finished":
            raise ValueError("Run status is finished; finished runs cannot be failed.")
        failed_at = _now()
        record["status"] = "failed"
        record["updatedAt"] = failed_at
        record["finishedAt"] = failed_at
        snapshot = _snapshot_files([self.run_json_path, self.events_path])
        try:
            self._save_run_record(record)
            self._event("run_failed", message)
        except Exception:
            _restore_files(snapshot)
            raise
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
    with _run_store_write_lock(run_store):
        return _start_run_unlocked(
            project=project,
            campaign=campaign,
            run_type=run_type,
            context=context,
            config=config,
            run_store=run_store,
            capabilities=capabilities,
        )


def _start_run_unlocked(
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
    selected_config = _validate_json_object(config or {}, "RunConfig")

    root = _run_store_root(run_store)
    run_id, run_dir = _allocate_run_dir(run_store)
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
    save_json(selected_config, run_dir / "config.json")
    save_json(
        _validate_run_manifest(
            {
                "kind": "openplazma.run_manifest",
                "version": "0.1.0",
                "runId": run_id,
                "createdAt": created_at,
                "updatedAt": created_at,
                "artifacts": [],
            },
            expected_run_id=run_id,
        ),
        run_dir / "manifest.json",
    )

    run = Run(run_dir)
    run._event("run_started", "Run started.")
    return run


def list_runs(run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    with _run_store_write_lock(run_store):
        runs_root = _runs_root(run_store)
        if not runs_root.exists():
            return []
        records = []
        for path in sorted(runs_root.iterdir()):
            if path.is_dir() and (path / "run.json").is_file():
                records.append(load_run(path.name, run_store))
        return records


def load_run(run_id: str, run_store: str | Path = ".openplazma") -> dict[str, Any]:
    with _run_store_write_lock(run_store):
        record = _validate_run_record(load_json(_run_dir(run_id, run_store) / "run.json"), expected_run_id=run_id)
        return _validate_run_store_consistency(
            record,
            manifest=load_manifest(run_id, run_store=run_store),
            metrics=load_metrics(run_id, run_store=run_store),
            events=load_events(run_id, run_store=run_store),
        )


def load_metrics(run_id: str, run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    with _run_store_write_lock(run_store):
        metrics = [
            _validate_metric_record(record, expected_run_id=run_id)
            for record in _read_jsonl(_run_dir(run_id, run_store) / "metrics.jsonl")
        ]
        _require_record_count_within_limit(len(metrics), MAX_METRICS_PER_RUN, "MAX_METRICS_PER_RUN", "MetricRecord")
        return metrics


def load_events(run_id: str, run_store: str | Path = ".openplazma") -> list[dict[str, Any]]:
    with _run_store_write_lock(run_store):
        events = [
            _validate_event_record(record, expected_run_id=run_id)
            for record in _read_jsonl(_run_dir(run_id, run_store) / "events.jsonl")
        ]
        return _validate_event_sequence(events)


def load_manifest(run_id: str, run_store: str | Path = ".openplazma") -> dict[str, Any]:
    with _run_store_write_lock(run_store):
        run_dir = _run_dir(run_id, run_store)
        manifest = _validate_run_manifest(load_json(run_dir / "manifest.json"), expected_run_id=run_id)
        return _validate_run_manifest_artifact_files(manifest, run_dir)


def log_context_signal_and_study_record(
    run: Run,
    context: dict[str, Any],
    signal: dict[str, Any],
    study_record: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    validated_context = validate_experiment_context(context)
    validated_signal = validate_signal_series(signal)
    validated_study_record = validate_study_record(study_record)
    return {
        "experiment_context": run.log_artifact("experiment_context", "experiment_context", validated_context),
        "signal_series": run.log_artifact("signal_series", "signal_series", validated_signal),
        "study_record": run.log_artifact("study_record", "study_record", validated_study_record),
    }


def runstore_output_hint(run: Run) -> str:
    return run.run_dir.as_posix()
