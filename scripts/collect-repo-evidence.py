#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback.
    tomllib = None


FACTS_VERSION = "repo-evidence-facts.v1"
EXCLUDED_DIRS = {
    ".agent-runs",
    ".cache",
    ".git",
    ".next",
    ".turbo",
    ".venv",
    "__pycache__",
    "Legacy",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}
PACKAGE_DEPENDENCY_SECTIONS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
)

MANIFEST_KINDS = {
    "package.json": "node-package-manifest",
    "package-lock.json": "node-npm-lockfile",
    "pnpm-lock.yaml": "node-pnpm-lockfile",
    "yarn.lock": "node-yarn-lockfile",
    "bun.lockb": "node-bun-lockfile",
    "pyproject.toml": "python-project-manifest",
    "requirements.txt": "python-requirements",
    "poetry.lock": "python-poetry-lockfile",
    "Pipfile": "python-pipfile",
    "Pipfile.lock": "python-pipfile-lockfile",
    "Cargo.toml": "rust-cargo-manifest",
    "Cargo.lock": "rust-cargo-lockfile",
    "go.mod": "go-module-manifest",
    "go.sum": "go-module-lockfile",
    "composer.json": "php-composer-manifest",
    "composer.lock": "php-composer-lockfile",
    "Gemfile": "ruby-bundler-manifest",
    "Gemfile.lock": "ruby-bundler-lockfile",
}

FRAMEWORK_CONFIG_KINDS = {
    "next.config.js": "nextjs-config",
    "next.config.mjs": "nextjs-config",
    "next.config.ts": "nextjs-config",
    "vite.config.js": "vite-config",
    "vite.config.ts": "vite-config",
    "nuxt.config.js": "nuxt-config",
    "nuxt.config.ts": "nuxt-config",
    "angular.json": "angular-config",
    "pytest.ini": "pytest-config",
    "tox.ini": "tox-config",
    "mypy.ini": "mypy-config",
    "ruff.toml": "ruff-config",
    ".ruff.toml": "ruff-config",
    "tsconfig.json": "typescript-config",
    "eslint.config.js": "eslint-config",
    ".eslintrc.json": "eslint-config",
    ".gitleaksignore": "gitleaks-ignore",
}

RUNTIME_VERSION_KINDS = {
    ".python-version": "python-version-file",
    ".node-version": "node-version-file",
    ".nvmrc": "node-version-file",
    ".ruby-version": "ruby-version-file",
    ".tool-versions": "tool-versions-file",
}

DOCKER_NAMES = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
IAC_SUFFIXES = (".tf",)
IAC_NAMES = {"Pulumi.yaml", "pulumi.yaml", "Chart.yaml", "kustomization.yaml", "kustomization.yml"}


def posix_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def limited(value: str, limit: int = 200) -> str:
    value = " ".join(value.strip().split())
    return value[:limit]


def read_text(path: Path, max_bytes: int = 131_072) -> str:
    try:
        raw = path.read_bytes()[:max_bytes]
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def load_json(path: Path) -> object | None:
    try:
        return json.loads(read_text(path))
    except Exception:  # noqa: BLE001 - malformed repo files are just facts gaps.
        return None


def load_toml(path: Path) -> dict:
    if tomllib is None:
        return {}
    try:
        return tomllib.loads(read_text(path))
    except Exception:  # noqa: BLE001
        return {}


def pin_values_for_manifest(path: Path, basename: str) -> list[str]:
    pins: list[str] = []
    parsed_json = load_json(path) if basename.endswith(".json") or basename.endswith(".lock") else None

    if isinstance(parsed_json, dict):
        for key in ["lockfileVersion", "packageManager", "version"]:
            value = parsed_json.get(key)
            if isinstance(value, (str, int, float)):
                pins.append(f"{key}={limited(str(value))}")
        if basename == "package.json":
            for section in PACKAGE_DEPENDENCY_SECTIONS:
                dependencies = parsed_json.get(section)
                if isinstance(dependencies, dict):
                    for package_name in sorted(dependencies):
                        value = dependencies[package_name]
                        if isinstance(value, (str, int, float)):
                            pins.append(f"{section}.{package_name}={limited(str(value))}")
        engines = parsed_json.get("engines")
        if isinstance(engines, dict):
            for key in sorted(engines):
                value = engines[key]
                if isinstance(value, str):
                    pins.append(f"engines.{key}={limited(value)}")

    if basename == "pyproject.toml":
        parsed_toml = load_toml(path)
        project = parsed_toml.get("project", {}) if isinstance(parsed_toml, dict) else {}
        if isinstance(project, dict):
            value = project.get("requires-python")
            if isinstance(value, str):
                pins.append(f"requires-python={limited(value)}")
        poetry = parsed_toml.get("tool", {}).get("poetry", {}) if isinstance(parsed_toml.get("tool"), dict) else {}
        if isinstance(poetry, dict):
            dependencies = poetry.get("dependencies", {})
            if isinstance(dependencies, dict):
                value = dependencies.get("python")
                if isinstance(value, str):
                    pins.append(f"tool.poetry.dependencies.python={limited(value)}")

    if basename in {"requirements.txt", "go.mod", "Gemfile.lock", "Cargo.lock", "poetry.lock"}:
        text = read_text(path, max_bytes=32_768)
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//")):
                continue
            if re.search(r"(==|~=|>=|<=|=|\s+v?\d)", stripped):
                pins.append(limited(stripped))
            if len(pins) >= 20:
                break

    return sorted(dict.fromkeys(pins))


def top_level_yaml_value(lines: list[str], key: str) -> str:
    prefix = f"{key}:"
    for index, raw in enumerate(lines):
        if not raw or raw[0].isspace() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith(prefix):
            value = raw[len(prefix) :].strip()
            if value:
                return limited(value)
            block: list[str] = []
            for next_raw in lines[index + 1 :]:
                if next_raw and not next_raw[0].isspace() and not next_raw.lstrip().startswith("#"):
                    break
                if next_raw.strip():
                    block.append(next_raw.rstrip())
            return limited("\\n".join(block))
    return ""


def workflow_fact(path: Path, root: Path) -> dict:
    lines = read_text(path, max_bytes=65_536).splitlines()
    return {
        "name": top_level_yaml_value(lines, "name"),
        "on": top_level_yaml_value(lines, "on"),
        "path": posix_rel(path, root),
        "permissions": top_level_yaml_value(lines, "permissions"),
    }


def discover_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, filenames in os.walk(root):
        dirs[:] = sorted(item for item in dirs if item not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            files.append(Path(current) / filename)
    return files


def under(path: str, prefix: str) -> bool:
    return path.startswith(prefix) and path != prefix.rstrip("/")


def collect(root: Path, target_source: str) -> dict:
    manifests: list[dict] = []
    framework_configs: list[dict] = []
    runtime_versions: list[dict] = []
    directory_signals: list[dict] = []
    infrastructure_signals: list[dict] = []
    workflows: list[dict] = []
    workflow_signals: list[dict] = []
    docker_paths: list[str] = []
    iac_paths: list[str] = []

    files = discover_files(root)
    rel_files = [posix_rel(path, root) for path in files]
    rel_file_set = set(rel_files)

    for path, rel_path in zip(files, rel_files, strict=True):
        basename = path.name
        if basename in MANIFEST_KINDS:
            manifests.append({
                "kind": MANIFEST_KINDS[basename],
                "path": rel_path,
                "version_pins": pin_values_for_manifest(path, basename),
            })
        if basename in FRAMEWORK_CONFIG_KINDS:
            framework_configs.append({"kind": FRAMEWORK_CONFIG_KINDS[basename], "path": rel_path})
        if basename in RUNTIME_VERSION_KINDS:
            version_lines = read_text(path, max_bytes=4096).splitlines()
            runtime_versions.append({
                "kind": RUNTIME_VERSION_KINDS[basename],
                "path": rel_path,
                "value": limited(version_lines[0] if version_lines else ""),
            })
        if basename in DOCKER_NAMES:
            docker_paths.append(rel_path)
            infrastructure_signals.append({"kind": "docker-present", "path": rel_path})
        if basename in IAC_NAMES or basename.endswith(IAC_SUFFIXES):
            iac_paths.append(rel_path)
            infrastructure_signals.append({"kind": "iac-present", "path": rel_path})
        if rel_path.startswith(".github/workflows/") and basename.endswith((".yml", ".yaml")):
            workflow = workflow_fact(path, root)
            workflows.append(workflow)
            workflow_signals.append({"kind": "workflow-present", "path": rel_path})
            if workflow["permissions"]:
                workflow_signals.append({"kind": "workflow-permissions-declared", "path": rel_path})
            if "schedule:" in workflow["on"]:
                workflow_signals.append({"kind": "workflow-schedule-declared", "path": rel_path})
            lower_path = rel_path.lower()
            lower_name = workflow["name"].lower()
            if "codeql" in lower_path or "codeql" in lower_name:
                workflow_signals.append({"kind": "workflow-codeql-named", "path": rel_path})
            if "security" in lower_path or "security" in lower_name:
                workflow_signals.append({"kind": "workflow-security-named", "path": rel_path})

    for directory in [
        ".github/workflows",
        ".agent-org/knowledge/ecosystems",
        ".agent-org/knowledge/domains",
        ".agent-org/knowledge/security-ci",
        ".agent-org/knowledge/cards",
        ".agent-org/knowledge/project",
        "src",
        "tests",
        "docs",
        "scripts",
        "schemas",
    ]:
        full = root / directory
        if full.is_dir():
            directory_signals.append({"kind": f"directory:{directory}", "path": directory})

    pack_ecosystem_cards = sorted(path for path in rel_file_set if under(path, ".agent-org/knowledge/ecosystems/"))
    pack_domain_cards = sorted(path for path in rel_file_set if under(path, ".agent-org/knowledge/domains/"))
    pack_security_ci_cards = sorted(path for path in rel_file_set if under(path, ".agent-org/knowledge/security-ci/"))
    repo_local_cards = sorted(
        path
        for path in rel_file_set
        if under(path, ".agent-org/knowledge/cards/") or under(path, ".agent-org/knowledge/project/")
    )

    facts = {
        "directory_signals": sorted(directory_signals, key=lambda item: (item["kind"], item["path"])),
        "docker_iac": {
            "docker_paths": sorted(docker_paths),
            "docker_present": bool(docker_paths),
            "iac_paths": sorted(iac_paths),
            "iac_present": bool(iac_paths),
        },
        "facts_version": FACTS_VERSION,
        "framework_configs": sorted(framework_configs, key=lambda item: (item["kind"], item["path"])),
        "infrastructure_signals": sorted(infrastructure_signals, key=lambda item: (item["kind"], item["path"])),
        "knowledge_cards": {
            "pack_domain_cards": pack_domain_cards,
            "pack_ecosystem_cards": pack_ecosystem_cards,
            "pack_security_ci_cards": pack_security_ci_cards,
            "repo_local_cards": repo_local_cards,
        },
        "manifests": sorted(manifests, key=lambda item: (item["kind"], item["path"])),
        "runtime_versions": sorted(runtime_versions, key=lambda item: (item["kind"], item["path"])),
        "target_root": {
            "path": ".",
            "path_semantics": "all emitted paths are relative to this target root",
            "source": target_source,
        },
        "workflows": sorted(workflows, key=lambda item: item["path"]),
        "workflow_signals": sorted(workflow_signals, key=lambda item: (item["kind"], item["path"])),
    }
    body = json.dumps(facts, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    facts["facts_digest"] = hashlib.sha256(body).hexdigest()
    return facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect judgment-free repository evidence facts.")
    parser.add_argument("--target", help="Target repository root. When omitted, uses the current directory deliberately.")
    parser.add_argument("--output", help="Write facts JSON to this path instead of stdout.")
    args = parser.parse_args(argv)

    target_arg = args.target if args.target is not None else "."
    target_source = "target-argument" if args.target is not None else "current-working-directory"
    root = Path(target_arg).resolve()
    if not root.is_dir():
        sys.stderr.write(f"target_invalid: {target_arg} is not a directory\n")
        return 1
    facts = collect(root, target_source)
    payload = json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
