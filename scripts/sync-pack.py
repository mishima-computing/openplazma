#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


MANIFEST_NAME = "pack-manifest.json"
STAMP_REL = ".agent-org/pack-version"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def invalid_manifest_path(path: object) -> str | None:
    if not isinstance(path, str) or not path:
        return "path must be a non-empty string"
    if path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path):
        return "path must be relative"
    stripped = path.rstrip("/")
    if not stripped:
        return "path must not be repository root"
    parts = stripped.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return "path must not contain empty, '.', or '..' segments"
    return None


def contained_path(root: Path, rel_path: str) -> Path | None:
    root_resolved = root.resolve()
    candidate = (root_resolved / rel_path.rstrip("/")).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def load_manifest(upstream: Path) -> tuple[dict | None, str | None, str | None]:
    manifest_path = upstream / MANIFEST_NAME
    try:
        raw = manifest_path.read_bytes()
        loaded = json.loads(raw.decode("utf-8"))
    except FileNotFoundError:
        return None, None, f"manifest_parse_error: {MANIFEST_NAME}: missing"
    except UnicodeDecodeError as exc:
        return None, None, f"manifest_parse_error: {MANIFEST_NAME}: utf8_decode_error: {exc}"
    except json.JSONDecodeError as exc:
        return None, None, f"manifest_parse_error: {MANIFEST_NAME}: {exc}"
    except OSError as exc:
        return None, None, f"manifest_parse_error: {MANIFEST_NAME}: {exc}"

    if not isinstance(loaded, dict):
        return None, None, f"manifest_parse_error: {MANIFEST_NAME}: root must be object"
    entries = loaded.get("entries")
    if not isinstance(entries, list):
        return None, None, f"manifest_parse_error: {MANIFEST_NAME}: entries must be array"
    return loaded, hashlib.sha256(raw).hexdigest(), None


def validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    entries = manifest.get("entries", [])
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"manifest_parse_error: entries[{index}] must be object")
            continue
        raw_path = entry.get("path")
        path_error = invalid_manifest_path(raw_path)
        if path_error:
            errors.append(f"manifest_parse_error: entries[{index}].path: {path_error}")
            continue
        path = str(raw_path)
        normalized = path.rstrip("/") + ("/" if path.endswith("/") else "")
        if normalized in seen:
            errors.append(f"manifest_parse_error: duplicate path: {normalized}")
        seen.add(normalized)
        if entry.get("type") not in {"file", "dir"}:
            errors.append(f"manifest_parse_error: {path}: type must be file or dir")
        if entry.get("tier") not in {"pack_level", "repo_local"}:
            errors.append(f"manifest_parse_error: {path}: tier must be pack_level or repo_local")
        if entry.get("check_applicability") not in {"source_only", "everywhere"}:
            errors.append(f"manifest_parse_error: {path}: check_applicability must be source_only or everywhere")
        if entry.get("type") == "dir" and not path.endswith("/"):
            errors.append(f"manifest_parse_error: {path}: dir paths must end with /")
        if entry.get("type") == "file" and path.endswith("/"):
            errors.append(f"manifest_parse_error: {path}: file paths must not end with /")
    return errors


def git_commit(upstream: Path) -> str:
    if not (upstream / ".git").exists():
        return "unknown"
    try:
        result = subprocess.run(
            ["git", "-C", str(upstream), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    commit = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
        return "unknown"
    return commit.lower()


def pack_entries(manifest: dict) -> list[dict]:
    entries = [entry for entry in manifest.get("entries", []) if isinstance(entry, dict) and entry.get("tier") == "pack_level"]
    return sorted(entries, key=lambda item: (0 if item.get("type") == "dir" else 1, str(item.get("path"))))


def declared_dir_paths(entries: list[dict]) -> set[str]:
    return {str(entry["path"]).rstrip("/") for entry in entries if entry.get("type") == "dir"}


def parent_dirs_declared(path: str, dirs: set[str]) -> bool:
    parts = path.split("/")[:-1]
    for index in range(1, len(parts) + 1):
        parent = "/".join(parts[:index])
        if parent and parent not in dirs:
            return False
    return True


def copy_pack(upstream: Path, target: Path, manifest: dict, manifest_hash: str, expect_commit: str | None) -> tuple[list[dict], list[str]]:
    diff: list[dict] = []
    errors: list[str] = []
    entries = pack_entries(manifest)
    dir_paths = declared_dir_paths(entries)
    file_hashes: dict[str, str] = {}

    upstream = upstream.resolve()
    target = target.resolve()
    commit = git_commit(upstream)
    if expect_commit and commit != expect_commit:
        errors.append(f"upstream_commit_mismatch: expected {expect_commit}, got {commit}")
        return diff, errors

    for entry in entries:
        rel_path = str(entry["path"])
        source_path = contained_path(upstream, rel_path)
        target_path = contained_path(target, rel_path)
        if source_path is None:
            errors.append(f"manifest_path_escape: source path escapes upstream root: {rel_path}")
            continue
        if target_path is None:
            errors.append(f"manifest_path_escape: target path escapes target root: {rel_path}")
            continue

        if entry.get("type") == "dir":
            if target_path.exists() and not target_path.is_dir():
                errors.append(f"target_type_conflict: {rel_path} exists and is not a directory")
                continue
            if not target_path.exists():
                try:
                    target_path.mkdir(parents=False, exist_ok=False)
                except FileNotFoundError:
                    errors.append(f"target_parent_missing: parent directory for {rel_path} is missing from manifest order")
                    continue
                except OSError as exc:
                    errors.append(f"target_write_error: {rel_path}: {exc}")
                    continue
                diff.append({"path": rel_path, "action": "created_dir"})
            continue

        if not parent_dirs_declared(rel_path, dir_paths):
            errors.append(f"manifest_parent_not_declared: {rel_path}")
            continue
        required = entry.get("required") is not False
        if not source_path.is_file():
            if required:
                errors.append(f"source_missing: {rel_path}")
            continue
        if target_path.exists() and not target_path.is_file():
            errors.append(f"target_type_conflict: {rel_path} exists and is not a file")
            continue

        try:
            source_hash = sha256_file(source_path)
            target_hash = sha256_file(target_path) if target_path.is_file() else None
        except OSError as exc:
            errors.append(f"file_hash_error: {rel_path}: {exc}")
            continue

        if target_hash != source_hash:
            try:
                shutil.copyfile(source_path, target_path)
            except OSError as exc:
                errors.append(f"target_write_error: {rel_path}: {exc}")
                continue
            action = "updated" if target_hash is not None else "created"
            diff.append({"path": rel_path, "action": action})

        try:
            copied_hash = sha256_file(target_path)
        except OSError as exc:
            errors.append(f"file_hash_error: {rel_path}: {exc}")
            continue
        if copied_hash != source_hash:
            errors.append(f"byte_identity_mismatch: {rel_path}")
            continue
        file_hashes[rel_path] = source_hash

    if errors:
        return diff, errors

    stamp = {
        "upstream_commit": commit,
        "synced_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "manifest_sha256": manifest_hash,
        "files": dict(sorted(file_hashes.items())),
    }
    stamp_path = contained_path(target, STAMP_REL)
    if stamp_path is None:
        return diff, [f"manifest_path_escape: target path escapes target root: {STAMP_REL}"]
    if ".agent-org" not in dir_paths and not stamp_path.parent.is_dir():
        return diff, [f"manifest_parent_not_declared: {STAMP_REL}"]
    try:
        stamp_path.parent.mkdir(parents=False, exist_ok=True)
        stamp_path.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        errors.append(f"target_write_error: {STAMP_REL}: {exc}")
    return diff, errors


def emit(diff: list[dict], errors: list[str]) -> int:
    payload = {
        "status": "pass" if not errors else "fail",
        "diff": diff,
        "errors": errors,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync AI Quality Bootstrap pack files from a local upstream.")
    parser.add_argument("upstream", help="Local upstream source pack path.")
    parser.add_argument("--target", default=".", help="Target repository root. Defaults to current directory.")
    parser.add_argument("--expect-commit", help="Require the upstream git commit to match this SHA.")
    args = parser.parse_args(argv)

    upstream = Path(args.upstream)
    target = Path(args.target)
    if not upstream.is_dir():
        return emit([], [f"upstream_invalid: {args.upstream} is not a directory"])
    if not target.is_dir():
        return emit([], [f"target_invalid: {args.target} is not a directory"])

    manifest, manifest_hash, manifest_error = load_manifest(upstream)
    if manifest_error or manifest is None or manifest_hash is None:
        return emit([], [manifest_error or f"manifest_parse_error: {MANIFEST_NAME}: unavailable"])
    manifest_errors = validate_manifest(manifest)
    if manifest_errors:
        return emit([], manifest_errors)

    diff, errors = copy_pack(upstream, target, manifest, manifest_hash, args.expect_commit)
    return emit(diff, errors)


if __name__ == "__main__":
    sys.exit(main())
