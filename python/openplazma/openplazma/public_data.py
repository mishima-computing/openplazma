from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ._json import load_json
from ._validation import require_iso_datetime, require_keys, require_list, require_mapping, require_string
from .records import load_study_record
from .signals import build_signal_channel_index, validate_signal_series
from .sources import validate_data_provider

PUBLIC_OBSERVATION_PROVIDER = "NOAA_SWPC"
REAL_FIXTURE_MANIFEST = Path("data") / "fixtures" / "real" / "manifest.json"

_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(value: Any, name: str) -> str:
    digest = require_string(value, name)
    if _SHA256_RE.fullmatch(digest) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest.")
    return digest


def _require_nonnegative_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer.")
    return value


def _repo_relative_path(repo_root: str | Path, value: Any, name: str) -> Path:
    relative = Path(require_string(value, name))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{name} must be a repo-relative path.")

    root = Path(repo_root).resolve()
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{name} must stay inside the repository root.")
    return resolved


def validate_public_observation_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = require_mapping(manifest, "PublicObservationManifest")
    require_keys(manifest, ["kind", "version", "datasetId", "provider", "shots"], "PublicObservationManifest")
    if manifest["kind"] != "openplazma.fixture_manifest":
        raise ValueError("PublicObservationManifest.kind must be openplazma.fixture_manifest.")
    if manifest["version"] != "0.1.0":
        raise ValueError("PublicObservationManifest.version must be 0.1.0.")
    require_string(manifest["datasetId"], "PublicObservationManifest.datasetId")
    provider = validate_data_provider(manifest["provider"], "PublicObservationManifest.provider")
    if provider != PUBLIC_OBSERVATION_PROVIDER:
        raise ValueError(f"PublicObservationManifest.provider must be {PUBLIC_OBSERVATION_PROVIDER}.")

    shots = require_list(manifest["shots"], "PublicObservationManifest.shots")
    if len(shots) == 0:
        raise ValueError("PublicObservationManifest.shots must include at least one shot.")
    seen_shot_ids: set[str] = set()
    for index, shot_ref in enumerate(shots):
        shot = require_mapping(shot_ref, f"PublicObservationManifest.shots[{index}]")
        require_keys(shot, ["shotId", "path"], f"PublicObservationManifest.shots[{index}]")
        shot_id = require_string(shot["shotId"], f"PublicObservationManifest.shots[{index}].shotId")
        require_string(shot["path"], f"PublicObservationManifest.shots[{index}].path")
        if shot_id in seen_shot_ids:
            raise ValueError(f"Duplicate public observation shotId '{shot_id}'.")
        seen_shot_ids.add(shot_id)
    return manifest


def load_public_observation_manifest(repo_root: str | Path) -> dict[str, Any]:
    return validate_public_observation_manifest(load_json(Path(repo_root) / REAL_FIXTURE_MANIFEST))


def list_public_observation_snapshots(repo_root: str | Path) -> list[dict[str, Any]]:
    manifest = load_public_observation_manifest(repo_root)
    return [
        {
            "datasetId": manifest["datasetId"],
            "provider": manifest["provider"],
            "shotId": shot["shotId"],
            "path": shot["path"],
        }
        for shot in manifest["shots"]
    ]


def validate_source_provenance(provenance: dict[str, Any], repo_root: str | Path) -> dict[str, Any]:
    provenance = require_mapping(provenance, "SourceProvenance")
    require_keys(
        provenance,
        [
            "kind",
            "version",
            "provider",
            "sourceLabel",
            "retrievedAt",
            "sourcePages",
            "rawFiles",
            "bundleSha256",
            "limitations",
        ],
        "SourceProvenance",
    )
    if provenance["kind"] != "openplazma.source_provenance":
        raise ValueError("SourceProvenance.kind must be openplazma.source_provenance.")
    if provenance["version"] != "0.1.0":
        raise ValueError("SourceProvenance.version must be 0.1.0.")
    provider = validate_data_provider(provenance["provider"], "SourceProvenance.provider")
    if provider != PUBLIC_OBSERVATION_PROVIDER:
        raise ValueError(f"SourceProvenance.provider must be {PUBLIC_OBSERVATION_PROVIDER}.")
    require_string(provenance["sourceLabel"], "SourceProvenance.sourceLabel")
    require_iso_datetime(provenance["retrievedAt"], "SourceProvenance.retrievedAt")
    bundle_sha256 = _require_sha256(provenance["bundleSha256"], "SourceProvenance.bundleSha256")

    source_pages = require_list(provenance["sourcePages"], "SourceProvenance.sourcePages")
    if len(source_pages) == 0:
        raise ValueError("SourceProvenance.sourcePages must include at least one source page.")
    for index, source_page in enumerate(source_pages):
        require_string(source_page, f"SourceProvenance.sourcePages[{index}]")

    limitations = require_list(provenance["limitations"], "SourceProvenance.limitations")
    if len(limitations) == 0:
        raise ValueError("SourceProvenance.limitations must include at least one limitation.")
    for index, limitation in enumerate(limitations):
        require_string(limitation, f"SourceProvenance.limitations[{index}]")

    raw_files = require_list(provenance["rawFiles"], "SourceProvenance.rawFiles")
    if len(raw_files) == 0:
        raise ValueError("SourceProvenance.rawFiles must include at least one raw file.")
    for index, raw_file_ref in enumerate(raw_files):
        raw_file = require_mapping(raw_file_ref, f"SourceProvenance.rawFiles[{index}]")
        require_keys(raw_file, ["name", "url", "path", "sha256", "bytes"], f"SourceProvenance.rawFiles[{index}]")
        name = require_string(raw_file["name"], f"SourceProvenance.rawFiles[{index}].name")
        require_string(raw_file["url"], f"SourceProvenance.rawFiles[{index}].url")
        expected_sha256 = _require_sha256(raw_file["sha256"], f"SourceProvenance.rawFiles[{index}].sha256")
        expected_bytes = _require_nonnegative_int(raw_file["bytes"], f"SourceProvenance.rawFiles[{index}].bytes")
        raw_path = _repo_relative_path(repo_root, raw_file["path"], f"SourceProvenance.rawFiles[{index}].path")
        if raw_path.name != name:
            raise ValueError(f"SourceProvenance.rawFiles[{index}].name must match the raw file path basename.")
        if not raw_path.is_file():
            raise ValueError(f"SourceProvenance.rawFiles[{index}].path must point to an existing local file.")
        actual_bytes = raw_path.stat().st_size
        if actual_bytes != expected_bytes:
            raise ValueError(f"SourceProvenance.rawFiles[{index}].bytes does not match local file size.")
        actual_sha256 = _sha256(raw_path)
        if actual_sha256 != expected_sha256:
            raise ValueError(f"SourceProvenance.rawFiles[{index}].sha256 does not match local file.")

    bundle_seed = json.dumps(raw_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    actual_bundle_sha256 = hashlib.sha256(bundle_seed).hexdigest()
    if actual_bundle_sha256 != bundle_sha256:
        raise ValueError("SourceProvenance.bundleSha256 does not match raw file metadata.")

    return provenance


def _select_shot(manifest: dict[str, Any], shot_id: str | None) -> dict[str, Any]:
    shots = manifest["shots"]
    if shot_id is None:
        if len(shots) != 1:
            raise ValueError("shot_id is required when more than one public observation snapshot is registered.")
        return shots[0]
    for shot in shots:
        if shot["shotId"] == shot_id:
            return shot
    raise ValueError(f"Public observation snapshot '{shot_id}' was not found.")


def load_public_observation_snapshot(repo_root: str | Path, shot_id: str | None = None) -> dict[str, Any]:
    manifest = load_public_observation_manifest(repo_root)
    shot_ref = _select_shot(manifest, shot_id)
    record_path = _repo_relative_path(repo_root, shot_ref["path"], "PublicObservationSnapshot.path")
    record = load_study_record(record_path)

    selected_shot_id = shot_ref["shotId"]
    if record["source"]["provider"] != PUBLIC_OBSERVATION_PROVIDER:
        raise ValueError(f"Public observation snapshot source provider must be {PUBLIC_OBSERVATION_PROVIDER}.")
    if record["source"]["shotId"] != selected_shot_id:
        raise ValueError("Public observation snapshot record source shotId must match the manifest.")
    if record["shotRef"]["shotId"] != selected_shot_id:
        raise ValueError("Public observation snapshot shotRef must match the manifest.")
    if record["context"]["datasetId"] != manifest["datasetId"]:
        raise ValueError("Public observation snapshot datasetId must match the manifest.")
    if record["context"]["safetyClassification"] != "public-web-observation":
        raise ValueError("Public observation snapshot must be classified as public-web-observation.")
    if record["context"]["capabilities"]["readFacilityTelemetry"] is not False:
        raise ValueError("Public observation snapshot must not read facility telemetry.")
    if record["context"]["capabilities"]["controlFacility"] is not False:
        raise ValueError("Public observation snapshot must not expose facility control.")

    provenance_path = _repo_relative_path(repo_root, record["source"]["uri"], "PublicObservationSnapshot.source.uri")
    provenance = validate_source_provenance(load_json(provenance_path), repo_root)
    if provenance["bundleSha256"] != record["source"]["sha256"]:
        raise ValueError("Public observation source sha256 must match SourceProvenance.bundleSha256.")
    if provenance["provider"] != record["source"]["provider"]:
        raise ValueError("Public observation source provider must match SourceProvenance.provider.")
    if provenance["sourceLabel"] != record["source"]["sourceLabel"]:
        raise ValueError("Public observation sourceLabel must match SourceProvenance.sourceLabel.")
    if record["context"]["source"]["sha256"] != provenance["bundleSha256"]:
        raise ValueError("Public observation context source sha256 must match SourceProvenance.bundleSha256.")
    if record["shot"]["source"]["sha256"] != provenance["bundleSha256"]:
        raise ValueError("Public observation shot source sha256 must match SourceProvenance.bundleSha256.")

    signals = [validate_signal_series(signal) for signal in record["signals"]]
    return {
        "datasetId": manifest["datasetId"],
        "provider": manifest["provider"],
        "shotId": selected_shot_id,
        "manifestPath": REAL_FIXTURE_MANIFEST.as_posix(),
        "recordPath": shot_ref["path"],
        "provenancePath": record["source"]["uri"],
        "record": record,
        "provenance": provenance,
        "signals": signals,
        "signalIndex": build_signal_channel_index(signals),
        "capabilities": dict(record["context"]["capabilities"]),
        "limitations": list(record["limitations"]),
    }


def load_public_observation_signal(repo_root: str | Path, shot_id: str, signal_id: str) -> dict[str, Any]:
    snapshot = load_public_observation_snapshot(repo_root, shot_id)
    require_string(signal_id, "PublicObservationSignal.signal_id")
    for signal in snapshot["signals"]:
        if signal["signalId"] == signal_id:
            return validate_signal_series(signal)
    raise ValueError(f"Signal '{signal_id}' was not found in public observation snapshot '{shot_id}'.")
