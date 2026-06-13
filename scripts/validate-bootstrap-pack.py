#!/usr/bin/env python3
from __future__ import annotations

import json
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK_MANIFEST = ROOT / "pack-manifest.json"
PACK_VERSION = ROOT / ".agent-org/pack-version"
SOURCE_REPO_SLUG = "mishima-computing/ai-org-bootstrap"

FINAL_AGENTS = [
    "functional-ci-action-writer",
    "security-ci-action-writer",
    "nonfunctional-ci-action-writer",
    "aggressive-designer",
    "conservative-designer",
    "genius",
    "aufheben-designer",
    "implementer",
]

CODEX_ADAPTERS = [
    "functional-ci-action-writer",
    "nonfunctional-ci-action-writer",
    "conservative-designer",
    "implementer",
]

CLAUDE_ADAPTERS = [
    "security-ci-action-writer",
    "aggressive-designer",
    "genius",
    "aufheben-designer",
    "implementer",
]

REQUIRED_SCHEMAS = [
    "ci-action-writer-result.schema.json",
    "controller-disclosure.schema.json",
    "design-proposal.schema.json",
    "genius-packet.schema.json",
    "implementation-contract.schema.json",
    "implementation-result.schema.json",
    "linon-review.schema.json",
    "aufheben-verdict.schema.json",
]

DISTRIBUTION_REQUIRED_FILES = [
    "pack-manifest.json",
    "scripts/sync-pack.py",
]

ROLE_HEADINGS = [
    "# Role:",
    "## Purpose",
    "## Primary Carrier",
    "## Secondary Carrier",
    "## Authority",
    "## Forbidden Actions",
    "## Inputs",
    "## Required Output",
    "## Stop Conditions",
    "## Evidence Requirements",
    "## Interaction With Other Roles",
    "## Anti-patterns",
    "## Notes For Carrier Adapters",
]

SCHEMA_BY_AGENT = {
    "functional-ci-action-writer": "schemas/ci-action-writer-result.schema.json",
    "security-ci-action-writer": "schemas/ci-action-writer-result.schema.json",
    "nonfunctional-ci-action-writer": "schemas/ci-action-writer-result.schema.json",
    "aggressive-designer": "schemas/design-proposal.schema.json",
    "conservative-designer": "schemas/design-proposal.schema.json",
    "genius": "schemas/genius-packet.schema.json",
    "aufheben-designer": "schemas/implementation-contract.schema.json",
    "implementer": "schemas/implementation-result.schema.json",
}


def sample_string(prefix: str, max_length: int = 200) -> str:
    return (prefix + " " + ("x" * max_length))[:max_length]


SCHEMA_SAMPLE_INSTANCES = {
    "schemas/ci-action-writer-result.schema.json": {
        "role_id": "functional-ci-action-writer",
        "detected_ecosystem": [],
        "workflows_read": [],
        "workflows_changed": [],
        "commands_added": [],
        "commands_already_present": [],
        "checks_added": [],
        "checks_already_present": [],
        "gaps": [],
        "files_changed": [],
    },
    "schemas/controller-disclosure.schema.json": {
        "run_id": "20260611-112527-abcdef0",
        "handoffs": [
            {
                "handoff": "designer-results-to-aufheben",
                "forwarded_verbatim": True,
                "source_sha256": "0" * 64,
                "controller_authored_text": [],
                "evaluative_language_added": [],
            }
        ],
    },
    "schemas/design-proposal.schema.json": {
        "role_id": "conservative-designer",
        "objective": "example objective",
        "proposal_summary": "example summary",
        "recommended_direction": "example direction",
        "expected_benefits": [],
        "risks": [],
        "assumptions": [],
        "constraints": [],
        "things_to_avoid": [],
        "handoff_notes": "example handoff",
        "confidence": {
            "overall_posture": "grounded",
            "grounded_claims": [
                {
                    "claim": "Design proposals are validated by a local schema.",
                    "evidence_ref": "schemas/design-proposal.schema.json",
                }
            ],
            "speculative_claims": [
                "A future proposal may need more repo evidence."
            ],
        },
        "continuity": {
            "selected_profiles": [sample_string(f"profile-{index}") for index in range(5)],
            "version_constraints": [sample_string(f"version-{index}") for index in range(6)],
            "ecosystem_facts_used": [sample_string(f"fact-{index}") for index in range(8)],
            "forbidden_expansions": [sample_string(f"forbidden-{index}") for index in range(6)],
            "safe_change_path": "s" * 600,
            "reversibility_plan": "r" * 600,
            "missing_safety_checks": [sample_string(f"check-{index}") for index in range(6)],
            "knowledge_gaps": [sample_string(f"gap-{index}") for index in range(6)],
        },
    },
    "schemas/genius-packet.schema.json": {
        "role_id": "genius",
        "objective": "example objective",
        "substrate_inputs": [
            {
                "ref_type": "repo_pointer",
                "locator": "roles/genius.md",
                "summary": "Example local role pointer.",
            }
        ],
        "official_spec_evidence": [
            {
                "ref_type": "official_spec",
                "locator": "https://example.com/spec",
                "summary": "Example named-interface specification evidence.",
            }
        ],
        "repo_evidence": [
            {
                "ref_type": "repo_pointer",
                "locator": "schemas/genius-packet.schema.json",
                "summary": "Example schema pointer.",
            }
        ],
        "kept_hypotheses": [
            {
                "hypothesis_id": "H1",
                "mechanism": "Use pointer-style evidence to keep handoff compact.",
                "score": 0.82,
                "verification_status": "confirmed",
                "repo_evidence_refs": [
                    {
                        "ref_type": "repo_pointer",
                        "locator": "roles/genius.md",
                        "summary": "Example role evidence reference.",
                    }
                ],
                "external_refs": [
                    {
                        "ref_type": "official_spec",
                        "locator": "https://example.com/spec",
                        "summary": "Example external verification reference.",
                    }
                ],
                "expected_benefit": "Example benefit.",
                "risks": [
                    "Example risk."
                ],
                "rejection_conditions": [
                    "Reject if localized evidence is absent."
                ],
                "what_not_to_copy": [
                    "Do not copy unrelated implementation bodies."
                ],
            }
        ],
        "refuted_hypotheses": [],
        "unverified_hypotheses": [],
        "what_not_to_copy": [
            "Do not perform search-first idea gathering."
        ],
        "handoff_to_aufheben": "example handoff",
    },
    "schemas/implementation-contract.schema.json": {
        "role_id": "aufheben-designer",
        "contract_id": "contract-example",
        "objective": "example objective",
        "selected_direction": "example direction",
        "rejected_parts": [
            {
                "source": "aggressive-designer",
                "rejected_part": "example rejected part",
                "reason": "example reason",
            }
        ],
        "implementation_summary": "example summary",
        "acceptance_criteria": [],
        "files_allowed_to_change": [],
        "files_not_allowed_to_change": [],
        "required_checks": [],
        "security_requirements": [],
        "nonfunctional_requirements": [],
        "non_goals": [],
        "risks": [],
        "fallback_plan": "example fallback",
        "handoff_to_implementer": "example handoff",
    },
    "schemas/implementation-result.schema.json": {
        "role_id": "implementer",
        "implementation_contract_id": "contract-example",
        "summary": "example summary",
        "files_changed": [],
        "commands_run": [],
        "command_results": [
            {
                "command": "true",
                "exit_code": 0,
                "result": "pass",
            }
        ],
        "checks_passed": [],
        "checks_failed": [],
        "remaining_failures": [],
        "scope_deviations": [],
        "manual_followup": [],
    },
    "schemas/linon-review.schema.json": {
        "profile_id": "linon-review",
        "findings": [
            {
                "file": "src/example.ts",
                "line_range": {
                    "start": 1,
                    "end": 2,
                },
                "severity": "critical",
                "lens": "forgeability",
                "basis": "static-read",
                "claim": "Client-writable evidence is accepted as authoritative.",
                "evidence_ref": "src/example.ts:1-2",
                "defect_locus": "implementation",
                "principle_id": "NN2",
            }
        ],
        "criterion_verdicts": [
            {
                "criterion_index": 0,
                "criterion_text_echo": "Example acceptance criterion.",
                "verdict": "refuted",
                "evidence_ref": "src/example.ts:1",
                "principle_id": "NN2",
            }
        ],
        "gaps": [
            {
                "kind": "truncation",
                "description": "No truncation applied.",
                "severity_first_truncation_applied": False,
            }
        ],
    },
    "schemas/ecosystem-profile-selection.schema.json": {
        "primary_ecosystem": [
            "python"
        ],
        "supporting_profiles": [
            "python-testing"
        ],
        "selected_profile_cards": [],
        "repo_local_cards": [
            ".agent-org/knowledge/cards/example.md"
        ],
        "evidence_refs": [
            "manifest:python-project-manifest: pyproject.toml"
        ],
        "selection_warnings": [],
        "knowledge_gaps": [
            "No pack ecosystem/domain profile cards were found under .agent-org/knowledge/ecosystems/ or .agent-org/knowledge/domains/."
        ],
    },
    "schemas/security-ci-profile-selection.schema.json": {
        "general_profile_enabled": True,
        "supporting_profiles": [
            "github-actions-general"
        ],
        "selected_profile_cards": [],
        "evidence_refs": [
            "workflow:present: .github/workflows/functional-ci.yml"
        ],
        "selection_warnings": [],
        "security_gaps": [
            "No security-ci profile cards were found under .agent-org/knowledge/security-ci/."
        ],
    },
    "schemas/aufheben-verdict.schema.json": {
        "role_id": "aufheben-designer",
        "decision": "redo",
        "situation_read": "Completeness is partial, reversibility is low, and confidence is speculative without repo evidence.",
        "redo_brief": {
            "targets": [
                "aggressive-designer",
                "genius",
            ],
            "diagnosis": "Missing a grounded alternative for an irreversible choice.",
            "new_info_or_angle_needed": [
                "Verify whether existing repo evidence supports the proposed boundary.",
            ],
        },
    },
}


class ValidationReadError(Exception):
    def __init__(self, path: Path, detail: str):
        self.path = path
        self.detail = detail
        super().__init__(f"{rel(path)}: {detail}")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValidationReadError(path, "missing") from None
    except IsADirectoryError:
        raise ValidationReadError(path, "is a directory") from None
    except OSError as exc:
        raise ValidationReadError(path, str(exc)) from None
    except UnicodeDecodeError as exc:
        raise ValidationReadError(path, f"utf8_decode_error: {exc}") from None


def format_read_error(exc: ValidationReadError) -> str:
    return f"file_read_error: {rel(exc.path)}: {exc.detail}"


def guarded(check_name: str, func, *args) -> list[str]:
    try:
        return func(*args)
    except ValidationReadError as exc:
        return [f"{check_name}: {format_read_error(exc)}"]


def contains_all(content: str, phrases: list[str]) -> list[str]:
    lowered = content.lower()
    return [phrase for phrase in phrases if phrase.lower() not in lowered]


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str, str | None]:
    content = text(path)
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content, "missing opening frontmatter fence"
    try:
        end_index = lines[1:].index("---") + 1
    except ValueError:
        return {}, content, "missing closing frontmatter fence"
    frontmatter: dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
    body = "\n".join(lines[end_index + 1 :])
    return frontmatter, body, None


ANCHOR_CITATION_RE = re.compile(r"\banchor:([a-z0-9-]+)#([a-z0-9-]+)\b")
ANCHOR_STABLE_ID_RE = re.compile(r"#([a-z0-9][a-z0-9-]*)\b")
PROHIBITION_RE = re.compile(r"\b(?:never|do not|avoid|forbid)\b", re.IGNORECASE)
ANCHOR_POINTER_RE = re.compile(r"^Pointer:\s+https?://\S+\s+\|\s+Date/version:\s+(.+?)\s+\|")

ANCHOR_PERSISTENCE_IDIOMS = {
    "dated-permalink": [
        re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
        re.compile(r"\bpublished\s+\d{4}-\d{2}\b", re.IGNORECASE),
    ],
    "edition-pinned": [
        re.compile(r"\bedition\b.*\b\d{4}\b", re.IGNORECASE),
        re.compile(r"\bedition\b", re.IGNORECASE),
        re.compile(r"\bv\d+(?:\.\d+)*\b.*\b\d{4}\b", re.IGNORECASE),
        re.compile(r",\s*\d{4}\b"),
    ],
    "living": [
        re.compile(r"\bchecked\s+\d{4}-\d{2}-\d{2};\s+re-check on\s+[^.]+", re.IGNORECASE),
        re.compile(r"\bcontroller follow-up required for date capture\b", re.IGNORECASE),
    ],
}

# Ledger-backed allowlist for existing UI prohibition lines.
UI_PROHIBITION_ALLOWLIST = [
    (".agent-org/knowledge/ui/README.md", "do not authorize selector inference"),
    (".agent-org/knowledge/ui/exemplars.md", "never cite bare domain"),
]

CARD_REQUIRED_ANCHOR_SLUGS = {
    "ui-bilingual-typography.md": [
        "typography-cjk-latin",
        "hierarchy-gestalt",
        "grid-layout",
    ],
    "ui-information-design.md": [
        "information-design",
        "grid-layout",
    ],
    "ui-feel-foundations.md": [
        "interaction-feedback",
        "motion",
    ],
    "ui-composition-patterns.md": [
        "composition",
        "grid-layout",
        "hierarchy-gestalt",
    ],
    "ui-corporate-trust-genre.md": [
        "genre-corporate-trust",
        "composition",
    ],
    "ui-gacha-genre.md": [
        "genre-gacha",
        "motion",
    ],
}

CLAIM_CLASS_CITATION_ROWS = [
    "ui-bilingual-typography.md",
    "ui-composition-patterns.md",
    "ui-corporate-trust-genre.md",
    "ui-information-design.md",
    "ui-feel-foundations.md",
]


def is_allowed_ui_prohibition(path: Path, line: str) -> bool:
    relative = rel(path)
    lowered = line.lower()
    return any(
        relative == allowed_path and substring.lower() in lowered
        for allowed_path, substring in UI_PROHIBITION_ALLOWLIST
    )


def discover_ui_anchors(ui_dir: Path) -> tuple[dict[str, set[str]], list[str]]:
    errors: list[str] = []
    anchors: dict[str, set[str]] = {}
    anchors_dir = ui_dir / "anchors"
    if not anchors_dir.is_dir():
        return anchors, errors

    for path in sorted(anchors_dir.glob("*.md")):
        content = text(path)
        nonblank_lines = [line for line in content.splitlines() if line.strip()]
        if len(nonblank_lines) > 40:
            errors.append(f"{rel(path)} anchor body must be at most 40 nonblank lines")

        slug = path.stem
        ids: set[str] = set()
        for line in content.splitlines():
            heading = re.match(r"^#{2,6}\s+([a-z0-9][a-z0-9-]*)\s*$", line.strip())
            if heading:
                ids.add(heading.group(1))
            if "stable id" in line.lower():
                ids.update(ANCHOR_STABLE_ID_RE.findall(line))
        anchors[slug] = ids
    return anchors, errors


def check_anchor_persistence_idioms(ui_dir: Path) -> list[str]:
    errors: list[str] = []
    anchors_dir = ui_dir / "anchors"
    if not anchors_dir.is_dir():
        return errors

    for path in sorted(anchors_dir.glob("*.md")):
        for line_number, line in enumerate(text(path).splitlines(), start=1):
            match = ANCHOR_POINTER_RE.match(line.strip())
            if not match:
                continue
            date_version = match.group(1)
            if not any(
                pattern.search(date_version)
                for patterns in ANCHOR_PERSISTENCE_IDIOMS.values()
                for pattern in patterns
            ):
                errors.append(f"{rel(path)}:{line_number} anchor pointer Date/version must declare persistence idiom")
    return errors


def check_ui_anchor_citations(ui_dir: Path, anchors: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    for path in sorted(ui_dir.glob("*.md")):
        content = text(path)
        for slug, anchor_id in ANCHOR_CITATION_RE.findall(content):
            if slug not in anchors:
                errors.append(f"{rel(path)} unresolved anchor citation: anchor:{slug}#{anchor_id} missing anchor file")
            elif anchor_id not in anchors[slug]:
                errors.append(f"{rel(path)} unresolved anchor citation: anchor:{slug}#{anchor_id} missing stable ID")
    return errors


def check_frontmatter_watch_anchor_refs(path: Path, frontmatter: dict[str, str]) -> list[str]:
    errors: list[str] = []
    evidence_refs = frontmatter.get("evidence_refs", "")
    for slug, anchor_id in ANCHOR_CITATION_RE.findall(evidence_refs):
        if anchor_id.endswith("-watch"):
            errors.append(f"{rel(path)} frontmatter evidence_refs must not cite watch anchor: anchor:{slug}#{anchor_id}")
    return errors


def check_ui_prohibition_lines(ui_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(ui_dir.rglob("*.md")):
        for line_number, line in enumerate(text(path).splitlines(), start=1):
            if PROHIBITION_RE.search(line) and not is_allowed_ui_prohibition(path, line):
                errors.append(f"{rel(path)}:{line_number} prohibition line lacks ledger annotation allowlist")
    return errors


def check_claim_class_citations(ui_dir: Path, anchors: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []
    if "claim-classes" not in anchors.get("evaluation-instruments", set()):
        errors.append(".agent-org/knowledge/ui/anchors/evaluation-instruments.md missing stable ID: #claim-classes")
    for filename in CLAIM_CLASS_CITATION_ROWS:
        path = ui_dir / filename
        content = text(path)
        if "anchor:evaluation-instruments#claim-classes" not in content:
            errors.append(f"{rel(path)} must cite anchor:evaluation-instruments#claim-classes for claim class")
        if re.search(r"never\s+(?:claim\s+)?(?:conversion|engagement|seo)|never\s+conversion", content, re.IGNORECASE):
            errors.append(f"{rel(path)} must retire legacy conversion/engagement/SEO claim prohibition prose")
    return errors


def parse_json_files() -> list[str]:
    errors: list[str] = []
    schema_ids: dict[str, str] = {}
    for path in sorted((ROOT / "schemas").glob("*.json")):
        try:
            parsed = json.loads(text(path))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{rel(path)}: {exc}")
            continue
        schema_id = parsed.get("$id")
        if schema_id:
            if schema_id in schema_ids:
                errors.append(f"duplicate_schema_id: {schema_id} in {schema_ids[schema_id]} and {rel(path)}")
            schema_ids[schema_id] = rel(path)
    settings = ROOT / ".claude/settings.json"
    if settings.is_file():
        try:
            json.loads(text(settings))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{rel(settings)}: {exc}")
    return errors


def load_json(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(text(path)), None
    except ValidationReadError as exc:
        return None, format_read_error(exc)
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


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


def load_pack_manifest() -> tuple[dict | None, list[str]]:
    loaded, error = load_json(PACK_MANIFEST)
    if error:
        return None, [f"manifest_parse_error: pack-manifest.json: {error}"]
    if not isinstance(loaded, dict):
        return None, ["manifest_parse_error: pack-manifest.json: root must be object"]
    entries = loaded.get("entries")
    if not isinstance(entries, list):
        return None, ["manifest_parse_error: pack-manifest.json: entries must be array"]

    errors: list[str] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"manifest_parse_error: entries[{index}] must be object")
            continue
        raw_path = entry.get("path")
        path_error = invalid_manifest_path(raw_path)
        if path_error:
            errors.append(f"manifest_parse_error: entries[{index}].path: {path_error}")
            continue
        normalized = str(raw_path).rstrip("/") + ("/" if str(raw_path).endswith("/") else "")
        if normalized in seen:
            errors.append(f"manifest_parse_error: duplicate path: {normalized}")
        seen.add(normalized)
        if entry.get("type") not in {"file", "dir"}:
            errors.append(f"manifest_parse_error: {raw_path}: type must be file or dir")
        if entry.get("tier") not in {"pack_level", "repo_local"}:
            errors.append(f"manifest_parse_error: {raw_path}: tier must be pack_level or repo_local")
        if entry.get("check_applicability") not in {"source_only", "everywhere"}:
            errors.append(f"manifest_parse_error: {raw_path}: check_applicability must be source_only or everywhere")
        if entry.get("type") == "dir" and not str(raw_path).endswith("/"):
            errors.append(f"manifest_parse_error: {raw_path}: dir paths must end with /")
        if entry.get("type") == "file" and str(raw_path).endswith("/"):
            errors.append(f"manifest_parse_error: {raw_path}: file paths must not end with /")
        if "sha256" in entry:
            if entry.get("type") != "file":
                errors.append(f"manifest_parse_error: {raw_path}: sha256 is valid only for file entries")
            if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
                errors.append(f"manifest_parse_error: {raw_path}: sha256 must be lowercase hex")

    return (None, errors) if errors else (loaded, [])


def manifest_required_files(manifest: dict) -> list[str]:
    required: list[str] = []
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("tier") != "pack_level" or entry.get("type") != "file":
            continue
        if entry.get("required") is False:
            continue
        required.append(str(entry["path"]))
    return sorted(required)


def manifest_pack_files(manifest: dict) -> list[str]:
    files: list[str] = []
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("tier") == "pack_level" and entry.get("type") == "file":
            files.append(str(entry["path"]))
    return sorted(files)


def manifest_entry_sets(manifest: dict) -> tuple[set[str], set[str], set[str]]:
    files: set[str] = set()
    dirs: set[str] = set()
    repo_local_dirs: set[str] = set()
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict):
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str):
            continue
        path = raw_path.rstrip("/") + ("/" if raw_path.endswith("/") else "")
        if entry.get("type") == "file":
            files.add(path)
        elif entry.get("type") == "dir":
            dirs.add(path)
            if entry.get("tier") == "repo_local":
                repo_local_dirs.add(path)
    return files, dirs, repo_local_dirs


def pack_level_dirs(manifest: dict) -> set[str]:
    dirs: set[str] = set()
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("tier") == "pack_level" and entry.get("type") == "dir":
            raw_path = entry.get("path")
            if isinstance(raw_path, str):
                dirs.add(raw_path.rstrip("/") + "/")
    return dirs


def parent_dirs_declared(path: str, declared_dirs: set[str]) -> list[str]:
    missing: list[str] = []
    parts = path.rstrip("/").split("/")[:-1]
    for index in range(1, len(parts) + 1):
        parent = "/".join(parts[:index]) + "/"
        if parent not in declared_dirs:
            missing.append(parent)
    return missing


def is_under_any_dir(path: str, dirs: set[str]) -> bool:
    return any(path.startswith(item) for item in dirs)


def should_skip_completeness_path(path: Path) -> bool:
    return any(part in {"__pycache__", ".git"} for part in path.parts)


def check_manifest_completeness_for_root(root: Path, manifest: dict, label: str) -> list[str]:
    errors: list[str] = []
    manifest_files, manifest_dirs, repo_local_dirs = manifest_entry_sets(manifest)
    declared_pack_dirs = pack_level_dirs(manifest)
    found_files: set[str] = set()

    for directory in sorted(declared_pack_dirs):
        absolute_dir = root / directory
        if not absolute_dir.is_dir():
            continue
        for path in sorted(absolute_dir.rglob("*")):
            if should_skip_completeness_path(path) or not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            if is_under_any_dir(relative, repo_local_dirs):
                continue
            found_files.add(relative)

    for found in sorted(found_files):
        if found not in manifest_files:
            errors.append(f"{label}: manifest_completeness_missing_file: {found}")
        missing_parents = parent_dirs_declared(found, manifest_dirs)
        if missing_parents:
            errors.append(f"{label}: manifest_completeness_missing_parent_dirs: {found}: {missing_parents}")

    for path in sorted(manifest_files | manifest_dirs):
        if is_under_any_dir(path, repo_local_dirs) or path in repo_local_dirs:
            continue
        missing_parents = parent_dirs_declared(path, manifest_dirs)
        if missing_parents:
            errors.append(f"{label}: manifest_parent_dirs_missing: {path}: {missing_parents}")

    return errors


def check_pack_manifest_completeness(manifest: dict) -> list[str]:
    return check_manifest_completeness_for_root(ROOT, manifest, "source")


def check_pack_manifest_completeness_negative_fixture() -> list[str]:
    fixture_root = ROOT / "fixtures/pack-completeness/under-listed-tree"
    manifest_path = fixture_root / "pack-manifest.json"
    loaded, error = load_json(manifest_path)
    if error or not isinstance(loaded, dict):
        return [f"pack_completeness_fixture_invalid: {error or 'manifest must be object'}"]
    errors = check_manifest_completeness_for_root(fixture_root, loaded, "under-listed-tree-fixture")
    if not any("manifest_completeness_missing_file: pack/missing.txt" in item for item in errors):
        return ["pack_completeness_fixture_failed: under-listed-tree fixture did not report pack/missing.txt red"]
    return []


def check_manifest_recorded_hashes(manifest: dict) -> list[str]:
    errors: list[str] = []
    for entry in manifest.get("entries", []):
        if not isinstance(entry, dict) or "sha256" not in entry:
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str):
            continue
        path = ROOT / raw_path
        if not path.is_file():
            errors.append(f"manifest_hash_missing_file: {raw_path}")
            continue
        try:
            current_hash = sha256_file(path)
        except ValidationReadError as exc:
            errors.append(f"manifest_hash_read_error: {format_read_error(exc)}")
            continue
        if current_hash != entry["sha256"]:
            errors.append(f"manifest_hash_mismatch: {raw_path}")
    return errors


def legacy_required_files() -> list[str]:
    required = [
        "bootstrap/codex-bootstrap.md",
        "bootstrap/README.md",
        ".agent-org/runtime-registry.yaml",
        ".agent-org/execution-substrate.md",
        ".agent-org/tool-io-substrate.md",
        ".agent-org/knowledge/README.md",
        ".agent-org/worktree-policy.md",
        ".agent-org/artifact-policy.md",
        ".agent-org/pack-materialization.md",
        ".agent-org/carrier-invocation.md",
        ".agent-org/run-lifecycle.md",
        ".codex/config.toml",
        ".claude/settings.json",
        "scripts/run-gates.sh",
        "scripts/check-anchor-urls.py",
        "scripts/extract-claude-result.py",
        "scripts/hash-artifacts.py",
        "scripts/submit-result.py",
        "scripts/validate-bootstrap-pack.py",
    ]
    required.extend(DISTRIBUTION_REQUIRED_FILES)
    required.extend(f"roles/{agent}.md" for agent in FINAL_AGENTS + ["controller"])
    required.extend(f".codex/agents/{agent}.toml" for agent in CODEX_ADAPTERS)
    required.extend(f".claude/agents/{agent}.md" for agent in CLAUDE_ADAPTERS)
    required.extend(f"schemas/{name}" for name in REQUIRED_SCHEMAS)
    return sorted(required)


def check_pack_manifest_self_test(manifest: dict) -> list[str]:
    errors: list[str] = []
    expected = set(legacy_required_files())
    actual = set(manifest_required_files(manifest))
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"manifest_required_files_mismatch: missing legacy entries: {missing}")
    if extra:
        errors.append(f"manifest_required_files_mismatch: extra entries: {extra}")

    entries = manifest.get("entries", [])
    ecosystems = next((entry for entry in entries if isinstance(entry, dict) and entry.get("path") == ".agent-org/knowledge/ecosystems/"), None)
    domains = next((entry for entry in entries if isinstance(entry, dict) and entry.get("path") == ".agent-org/knowledge/domains/"), None)
    for name, entry in [("ecosystems", ecosystems), ("domains", domains)]:
        if not entry or entry.get("tier") != "pack_level" or entry.get("type") != "dir":
            errors.append(f"manifest_boundary_error: .agent-org/knowledge/{name}/ must be a pack_level dir")
    for path in [".agent-org/knowledge/cards/", ".agent-org/knowledge/project/", ".agent-org/history/", ".agent-runs/"]:
        entry = next((item for item in entries if isinstance(item, dict) and item.get("path") == path), None)
        if not entry or entry.get("tier") != "repo_local":
            errors.append(f"manifest_boundary_error: {path} must be repo_local")
    return errors


def check_tool_io_substrate() -> list[str]:
    path = ROOT / ".agent-org/tool-io-substrate.md"
    if not path.is_file():
        return ["tool_io_substrate_missing: .agent-org/tool-io-substrate.md"]

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"tool_io_substrate_unreadable: {exc}"]

    rows = [line for line in lines if line.lstrip().startswith("|")]
    errors: list[str] = []
    for script in sorted((ROOT / "scripts").glob("*.py")):
        basename = script.name
        matches = [row for row in rows if basename in row]
        if len(matches) != 1:
            errors.append(f"tool_io_substrate_audit_row_count: {basename}: expected 1, actual {len(matches)}")
            continue
        if "--self-test" not in script.read_text(encoding="utf-8") and "no `--self-test`" not in matches[0]:
            errors.append(f"tool_io_substrate_self_test_exception_missing: {basename}")
    return errors


def matches_json_type(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def validate_schema_instance(schema: dict, instance: object, path: str = "$") -> list[str]:
    errors: list[str] = []

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']!r}")

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        if not any(matches_json_type(instance, item) for item in expected_type):
            errors.append(f"{path}: expected type {expected_type!r}")
            return errors
    elif isinstance(expected_type, str):
        if not matches_json_type(instance, expected_type):
            errors.append(f"{path}: expected type {expected_type}")
            return errors

    if isinstance(instance, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in instance:
                    errors.append(f"{path}.{key}: missing required field")

        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for key, subschema in properties.items():
                if key in instance and isinstance(subschema, dict):
                    errors.extend(validate_schema_instance(subschema, instance[key], f"{path}.{key}"))

            if schema.get("additionalProperties") is False:
                for key in instance:
                    if key not in properties:
                        errors.append(f"{path}: additional property {key} is not allowed")

    if "if" in schema and isinstance(schema["if"], dict):
        condition_errors = validate_schema_instance(schema["if"], instance, path)
        if not condition_errors and isinstance(schema.get("then"), dict):
            errors.extend(validate_schema_instance(schema["then"], instance, path))

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for index, subschema in enumerate(all_of):
            if isinstance(subschema, dict):
                errors.extend(validate_schema_instance(subschema, instance, f"{path}.allOf[{index}]"))

    if isinstance(instance, list):
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(instance) > max_items:
            errors.append(f"{path}: expected at most {max_items} items")

        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(instance) < min_items:
            errors.append(f"{path}: expected at least {min_items} items")

        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate_schema_instance(item_schema, item, f"{path}[{index}]"))

    max_length = schema.get("maxLength")
    if isinstance(max_length, int) and isinstance(instance, str) and len(instance) > max_length:
        errors.append(
            f"{path}: expected string length at most {max_length} "
            f"(actual {len(instance)}, allowed {max_length})"
        )

    pattern = schema.get("pattern")
    if isinstance(pattern, str) and isinstance(instance, str):
        if not re.search(pattern, instance):
            errors.append(f"{path}: string does not match pattern {pattern!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and instance < minimum:
            errors.append(f"{path}: expected number at least {minimum}")

        maximum = schema.get("maximum")
        if isinstance(maximum, (int, float)) and instance > maximum:
            errors.append(f"{path}: expected number at most {maximum}")

    return errors


def check_design_proposal_role_conditionals(instance: object, path: str = "$") -> list[str]:
    if not isinstance(instance, dict):
        return []

    errors: list[str] = []
    if instance.get("role_id") == "conservative-designer" and "continuity" not in instance:
        errors.append(f"{path}: conservative-designer proposals must include continuity")
    return errors


def check_linon_review_conditionals(instance: object, path: str = "$") -> list[str]:
    if not isinstance(instance, dict):
        return []

    errors: list[str] = []
    findings = instance.get("findings", [])
    if isinstance(findings, list):
        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                continue
            line_range = finding.get("line_range")
            if not isinstance(line_range, dict):
                continue
            start = line_range.get("start")
            end = line_range.get("end")
            if (
                isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
                and end < start
            ):
                errors.append(f"{path}.findings[{index}].line_range: end must be >= start")
    return errors


def check_role_conditionals(schema_path: Path, instance: object, path: str = "$") -> list[str]:
    if rel(schema_path) == "schemas/design-proposal.schema.json":
        return check_design_proposal_role_conditionals(instance, path)
    if rel(schema_path) == "schemas/linon-review.schema.json":
        return check_linon_review_conditionals(instance, path)
    return []


def check_linon_review_fixtures() -> list[str]:
    errors: list[str] = []
    schema_path = ROOT / "schemas/linon-review.schema.json"
    schema, schema_error = load_json(schema_path)
    if schema_error or not isinstance(schema, dict):
        return [f"linon_review_fixture_schema_unavailable: {schema_error or 'schema must be object'}"]

    fixture_dir = ROOT / "fixtures/linon-review"
    expected_files = sorted(fixture_dir.glob("*.json"))
    if not expected_files:
        return ["linon_review_fixture_missing: no top-level fixtures/linon-review/*.json files found"]

    saw_valid = False
    saw_invalid = False
    for path in expected_files:
        instance, instance_error = load_json(path)
        if instance_error:
            errors.append(f"linon_review_fixture_parse_error: {rel(path)}: {instance_error}")
            continue
        validation_errors = validate_schema_instance(schema, instance)
        validation_errors.extend(check_role_conditionals(schema_path, instance))
        name = path.name
        if name.startswith("valid-"):
            saw_valid = True
            if validation_errors:
                errors.append(f"linon_review_fixture_expected_green_failed: {rel(path)}: {validation_errors}")
        elif name.startswith("invalid-"):
            saw_invalid = True
            if not validation_errors:
                errors.append(f"linon_review_fixture_expected_red_passed: {rel(path)}")
        else:
            errors.append(f"linon_review_fixture_unclassified: {rel(path)}")

        if name == "invalid-critical-missing-principle.json" and not any(
            "principle_id: missing required field" in item for item in validation_errors
        ):
            errors.append("linon_review_fixture_if_then_not_proven: invalid-critical-missing-principle.json")
        if name == "invalid-missing-evidence.json" and not any(
            "evidence_ref: missing required field" in item for item in validation_errors
        ):
            errors.append("linon_review_fixture_required_evidence_not_proven: invalid-missing-evidence.json")
        if name == "invalid-line-range.json" and not any(
            "line_range: end must be >= start" in item for item in validation_errors
        ):
            errors.append("linon_review_fixture_line_range_not_proven: invalid-line-range.json")

    if not saw_valid:
        errors.append("linon_review_fixture_missing_green")
    if not saw_invalid:
        errors.append("linon_review_fixture_missing_red")
    return errors


def check_linon_packet_fixture() -> list[str]:
    errors: list[str] = []
    packet_path = ROOT / "fixtures/linon-review/packet/example-packet.json"
    packet, packet_error = load_json(packet_path)
    if packet_error or not isinstance(packet, dict):
        return [f"linon_packet_fixture_invalid: {packet_error or 'packet must be object'}"]

    diff = packet.get("diff_artifact")
    contract = packet.get("implementation_contract")
    sha256_pair = packet.get("sha256_pair")
    if not isinstance(diff, dict):
        errors.append("linon_packet_fixture_invalid: diff_artifact must be object")
        diff = {}
    if not isinstance(contract, dict):
        errors.append("linon_packet_fixture_invalid: implementation_contract must be object")
        contract = {}
    if not isinstance(sha256_pair, dict):
        errors.append("linon_packet_fixture_invalid: sha256_pair must be object")
        sha256_pair = {}

    for label, item in [("diff_artifact", diff), ("implementation_contract", contract)]:
        raw_path = item.get("path")
        recorded_hash = item.get("sha256")
        path_error = invalid_manifest_path(raw_path)
        if path_error:
            errors.append(f"linon_packet_fixture_invalid: {label}.path: {path_error}")
            continue
        if not isinstance(recorded_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", recorded_hash):
            errors.append(f"linon_packet_fixture_invalid: {label}.sha256 must be lowercase hex")
            continue
        current_path = ROOT / str(raw_path)
        if not current_path.is_file():
            errors.append(f"linon_packet_fixture_missing: {raw_path}")
            continue
        current_hash = sha256_file(current_path)
        if current_hash != recorded_hash:
            errors.append(f"linon_packet_fixture_hash_mismatch: {label}: {raw_path}")

    diff_hash = diff.get("sha256")
    contract_hash = contract.get("sha256")
    if sha256_pair.get("diff_sha256") != diff_hash:
        errors.append("linon_packet_fixture_invalid: sha256_pair.diff_sha256 must match diff_artifact.sha256")
    if sha256_pair.get("contract_sha256") != contract_hash:
        errors.append("linon_packet_fixture_invalid: sha256_pair.contract_sha256 must match implementation_contract.sha256")

    embedded_contract = contract.get("embedded_contract")
    contract_path_value = contract.get("path")
    if isinstance(contract_path_value, str):
        contract_instance, contract_error = load_json(ROOT / contract_path_value)
        if contract_error:
            errors.append(f"linon_packet_fixture_contract_parse_error: {contract_path_value}: {contract_error}")
        else:
            if embedded_contract != contract_instance:
                errors.append("linon_packet_fixture_invalid: embedded_contract must equal contract file JSON")
            contract_schema, schema_error = load_json(ROOT / "schemas/implementation-contract.schema.json")
            if schema_error or not isinstance(contract_schema, dict):
                errors.append(f"linon_packet_fixture_contract_schema_unavailable: {schema_error or 'schema must be object'}")
            else:
                contract_errors = validate_schema_instance(contract_schema, contract_instance)
                if contract_errors:
                    errors.append(f"linon_packet_fixture_contract_invalid: {contract_errors}")

    note = packet.get("bootstrap_note")
    if not isinstance(note, str) or "bootstrap-only" not in note or "not an activation path" not in note:
        errors.append("linon_packet_fixture_invalid: bootstrap_note must mark inline diff review as bootstrap-only")

    return errors


def check_schema_samples() -> list[str]:
    errors: list[str] = []
    for rel_schema, sample in SCHEMA_SAMPLE_INSTANCES.items():
        schema_path = ROOT / rel_schema
        loaded, error = load_json(schema_path)
        if error or not isinstance(loaded, dict):
            errors.append(f"{rel_schema}: cannot load schema for required-field validation")
            continue

        sample_errors = validate_schema_instance(loaded, sample)
        for item in sample_errors:
            errors.append(f"{rel_schema}: sample invalid: {item}")

        conditional_errors = check_role_conditionals(schema_path, sample)
        for item in conditional_errors:
            errors.append(f"{rel_schema}: sample invalid: {item}")

        required = loaded.get("required", [])
        if isinstance(required, list) and required:
            missing_sample = dict(sample)
            missing_sample.pop(required[0], None)
            missing_errors = validate_schema_instance(loaded, missing_sample)
            if not missing_errors:
                errors.append(f"{rel_schema}: required field validation did not fail for {required[0]}")

    keyword_cases = [
        ({"type": "array", "maxItems": 1}, ["one", "two"], "maxItems"),
        ({"type": "array", "minItems": 1}, [], "minItems"),
        ({"type": "string", "maxLength": 3}, "four", "maxLength"),
        ({"type": "integer", "minimum": 2}, 1, "minimum"),
        (
            {
                "if": {
                    "properties": {
                        "severity": {
                            "type": "string",
                            "const": "critical",
                        }
                    },
                    "required": [
                        "severity"
                    ],
                },
                "then": {
                    "required": [
                        "principle_id"
                    ],
                },
            },
            {
                "severity": "critical"
            },
            "if/then",
        ),
    ]
    for schema, instance, keyword in keyword_cases:
        if not validate_schema_instance(schema, instance):
            errors.append(f"validate_schema_instance did not reject {keyword} violation")
    return errors


def check_schema_explicit_types() -> list[str]:
    errors: list[str] = []

    def walk(schema: dict, schema_path: str, json_path: str) -> None:
        if ("const" in schema or "enum" in schema) and "type" not in schema:
            errors.append(f"{schema_path}: {json_path}: const/enum schema must declare explicit type")

        properties = schema.get("properties")
        if isinstance(properties, dict):
            for key, subschema in properties.items():
                if isinstance(subschema, dict):
                    walk(subschema, schema_path, f"{json_path}.properties.{key}")

        items = schema.get("items")
        if isinstance(items, dict):
            walk(items, schema_path, f"{json_path}.items")

    for path in sorted((ROOT / "schemas").glob("*.json")):
        loaded, error = load_json(path)
        if error or not isinstance(loaded, dict):
            continue
        walk(loaded, rel(path), "$")

    return errors


def resolve_cli_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def validate_instance_cli(schema_arg: str, instance_arg: str) -> int:
    schema_path = resolve_cli_path(schema_arg)
    instance_path = resolve_cli_path(instance_arg)

    errors: list[str] = []
    schema, schema_error = load_json(schema_path)
    instance, instance_error = load_json(instance_path)

    if schema_error or not isinstance(schema, dict):
        errors.append(f"{schema_arg}: schema_parse_error: {schema_error or 'schema must be object'}")
    if instance_error:
        errors.append(f"{instance_arg}: json_parse_error: {instance_error}")

    if not errors and isinstance(schema, dict):
        errors.extend(validate_schema_instance(schema, instance))
        errors.extend(check_role_conditionals(schema_path, instance))

    payload = {
        "status": "pass" if not errors else "fail",
        "exit_code": 0 if not errors else 1,
        "schema": schema_arg,
        "instance": instance_arg,
        "errors": errors,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


def load_toml(paths: list[Path]) -> tuple[dict[Path, dict], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    parsed: dict[Path, dict] = {}
    try:
        import tomllib
    except ModuleNotFoundError:
        warnings.append("tomllib unavailable; skipped TOML parse")
        return parsed, errors, warnings
    for path in paths:
        try:
            parsed[path] = tomllib.loads(text(path))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{rel(path)}: {exc}")
    return parsed, errors, warnings


def check_required_files(manifest: dict) -> list[str]:
    errors: list[str] = []
    for item in manifest_required_files(manifest):
        path = ROOT / item
        if not path.is_file():
            errors.append(f"required_file_missing: {item}")
    return errors


def check_knowledge_cards() -> list[str]:
    errors: list[str] = []
    cards_dir = ROOT / ".agent-org/knowledge/cards"
    if not cards_dir.is_dir():
        return errors

    required_keys = {"name", "type", "source", "status"}
    allowed_types = {"constraint", "pitfall", "mechanism", "decision"}
    allowed_statuses = {"active", "superseded"}

    for path in sorted(cards_dir.glob("*.md")):
        frontmatter, _body, error = parse_frontmatter(path)
        if error:
            errors.append(f"{rel(path)} {error}")
            continue
        for key in sorted(required_keys - set(frontmatter)):
            errors.append(f"{rel(path)} missing frontmatter key: {key}")
        card_type = frontmatter.get("type")
        if card_type is not None and card_type not in allowed_types:
            errors.append(f"{rel(path)} type must be one of {sorted(allowed_types)}")
        status = frontmatter.get("status")
        if status is not None and status not in allowed_statuses:
            errors.append(f"{rel(path)} status must be one of {sorted(allowed_statuses)}")
    return errors


def check_ui_profile_cards() -> list[str]:
    errors: list[str] = []
    ui_dir = ROOT / ".agent-org/knowledge/ui"
    if not ui_dir.is_dir():
        return [".agent-org/knowledge/ui/ missing"]

    anchors, anchor_errors = discover_ui_anchors(ui_dir)
    errors.extend(anchor_errors)
    errors.extend(check_anchor_persistence_idioms(ui_dir))
    errors.extend(check_ui_anchor_citations(ui_dir, anchors))
    errors.extend(check_claim_class_citations(ui_dir, anchors))
    errors.extend(check_ui_prohibition_lines(ui_dir))

    readme = text(ui_dir / "README.md")
    for phrase in contains_all(readme, [
        "Profile Card Format",
        "profile_id",
        "scope",
        "covers",
        "freshness",
        "supersede_trigger",
        "evidence_refs",
        "evidence_refs cap: 6 pointers",
        "body cap: 12 nonblank lines",
        "exemplars",
        "exemplars cap: 4 pointers",
        "locale-pinned-URL@YYYY-MM-DD -> pattern-slug",
        "#32 pack/repo boundary",
        "Product-specific worldview cards",
        ".agent-org/knowledge/cards/",
        "#32 boundary",
    ]):
        errors.append(f".agent-org/knowledge/ui/README.md missing UI profile phrase: {phrase}")

    required_keys = {"profile_id", "scope", "covers", "freshness", "supersede_trigger", "evidence_refs"}
    optional_keys = {"exemplars"}
    required_cards = [
        "ui-feel-foundations.md",
        "ui-gacha-genre.md",
        "ui-bilingual-typography.md",
        "ui-composition-patterns.md",
        "ui-information-design.md",
        "ui-corporate-trust-genre.md",
    ]
    for filename in required_cards:
        path = ui_dir / filename
        if not path.is_file():
            errors.append(f"missing UI profile card: {rel(path)}")
            continue
        frontmatter, body, error = parse_frontmatter(path)
        if error:
            errors.append(f"{rel(path)} {error}")
            continue
        actual_keys = set(frontmatter)
        for key in sorted(required_keys - actual_keys):
            errors.append(f"{rel(path)} missing UI profile frontmatter key: {key}")
        for key in sorted(actual_keys - required_keys - optional_keys):
            errors.append(f"{rel(path)} unexpected UI profile frontmatter key: {key}")
        for key in sorted(required_keys & actual_keys):
            if not frontmatter[key]:
                errors.append(f"{rel(path)} empty UI profile frontmatter key: {key}")
        errors.extend(check_frontmatter_watch_anchor_refs(path, frontmatter))
        if frontmatter.get("profile_id") != path.stem:
            errors.append(f"{rel(path)} profile_id must match filename stem")
        evidence_refs = [item.strip() for item in frontmatter.get("evidence_refs", "").split(";") if item.strip()]
        if not evidence_refs:
            errors.append(f"{rel(path)} evidence_refs must contain at least one pointer")
        if len(evidence_refs) > 6:
            errors.append(f"{rel(path)} evidence_refs must contain at most 6 pointers")
        if "exemplars" in frontmatter:
            exemplars = [item.strip() for item in frontmatter["exemplars"].split(";") if item.strip()]
            if not exemplars:
                errors.append(f"{rel(path)} exemplars must contain at least one pointer when present")
            if len(exemplars) > 4:
                errors.append(f"{rel(path)} exemplars must contain at most 4 pointers")
            for item in exemplars:
                if not re.match(r"^https?://[^\s;]+@\d{4}-\d{2}-\d{2} -> [a-z0-9-]+$", item):
                    errors.append(f"{rel(path)} invalid exemplar pointer: {item}")
        nonblank_body_lines = [line for line in body.splitlines() if line.strip()]
        if len(nonblank_body_lines) > 12:
            errors.append(f"{rel(path)} body must be at most 12 nonblank lines")

        card_text = body.lower()
        if filename == "ui-feel-foundations.md":
            for phrase in contains_all(body, [
                "feel surfaces",
                "proves:",
                "timing-ranges",
                "multimodal cue",
                "silent fallback",
                "usability-performance gains require product measurement",
                "anchor:evaluation-instruments#claim-classes",
                "Hicks et al.",
            ]):
                errors.append(f"{rel(path)} missing feel profile phrase: {phrase}")
            if re.search(r"(?<![-/])\b\d+\s*ms\b(?!\s*[-/])", card_text):
                errors.append(f"{rel(path)} must not encode fixed ms constants")
        if filename == "ui-gacha-genre.md":
            for phrase in contains_all(body, [
                "rarity signaled before item",
                "rarity language",
                "anticipation",
                "pre-draw audit record",
                "short-horizon",
                "Yin & Xiao CHI 2022",
            ]):
                errors.append(f"{rel(path)} missing gacha profile phrase: {phrase}")
        if filename == "ui-bilingual-typography.md":
            for phrase in contains_all(body, [
                "Translation-only preserves structure",
                "Claim class: Legibility and focus are design-knowledge effects",
                "anchor:evaluation-instruments#claim-classes",
            ]):
                errors.append(f"{rel(path)} missing bilingual profile phrase: {phrase}")
        for required_slug in CARD_REQUIRED_ANCHOR_SLUGS.get(filename, []):
            if required_slug in anchors:
                citations = ANCHOR_CITATION_RE.findall(text(path))
                if not any(
                    slug == required_slug and anchor_id in anchors[slug]
                    for slug, anchor_id in citations
                ):
                    errors.append(f"{rel(path)} must cite a resolving anchor:{required_slug}# ID")
        if filename == "ui-composition-patterns.md":
            for phrase in contains_all(body, [
                "Decidable check",
                "Advisory check",
                "proof-artifact density per view",
                "consecutive same-type section cap",
                "one lead language per view",
                "plain-problem lead",
                "jargon lead",
                "Claim class: Focus, scanability, and credibility are design-knowledge effects",
                "anchor:evaluation-instruments#claim-classes",
            ]):
                errors.append(f"{rel(path)} missing composition profile phrase: {phrase}")
        if filename == "ui-information-design.md":
            for phrase in contains_all(body, [
                "図解",
                "A list must become a figure",
                "Label",
                "Claim class: Focus, scanability, and credibility are design-knowledge effects",
                "anchor:evaluation-instruments#claim-classes",
            ]):
                errors.append(f"{rel(path)} missing information-design profile phrase: {phrase}")
        if filename == "ui-corporate-trust-genre.md":
            for phrase in contains_all(body, [
                "K.K.-engagement provenance",
                "decision register",
                "決算公告 gravity",
                "company personhood",
                "trust-vs-LP register",
                "short-horizon",
                "Claim class: Focus, scanability, and credibility are design-knowledge effects",
                "anchor:evaluation-instruments#claim-classes",
            ]):
                errors.append(f"{rel(path)} missing corporate-trust profile phrase: {phrase}")
    return errors


def check_ecosystem_profile_cards() -> list[str]:
    errors: list[str] = []
    ecosystems_dir = ROOT / ".agent-org/knowledge/ecosystems"
    if not ecosystems_dir.is_dir():
        return [".agent-org/knowledge/ecosystems/ missing"]

    readme = text(ecosystems_dir / "README.md")
    for phrase in contains_all(readme, [
        "Ecosystem craft cards",
        "profile_id",
        "scope",
        "covers",
        "freshness",
        "supersede_trigger",
        "evidence_refs",
        "evidence_refs cap: 6 pointers",
        "body cap: 12 nonblank lines",
        "filename stem must equal `profile_id`",
        "mechanical repository evidence only",
        "pin:tailwindcss",
        "plain-CSS or CDN Tailwind repos without a package pin are a declared knowledge gap",
    ]):
        errors.append(f".agent-org/knowledge/ecosystems/README.md missing ecosystem profile phrase: {phrase}")

    required_keys = {"profile_id", "scope", "covers", "freshness", "supersede_trigger", "evidence_refs"}
    required_cards = [
        "htmlcss-computable-spatial.md",
        "htmlcss-modern-layout.md",
        "htmlcss-motion-implementation.md",
    ]
    for filename in required_cards:
        path = ecosystems_dir / filename
        if not path.is_file():
            errors.append(f"missing ecosystem profile card: {rel(path)}")
            continue
        frontmatter, body, error = parse_frontmatter(path)
        if error:
            errors.append(f"{rel(path)} {error}")
            continue
        actual_keys = set(frontmatter)
        for key in sorted(required_keys - actual_keys):
            errors.append(f"{rel(path)} missing ecosystem profile frontmatter key: {key}")
        for key in sorted(actual_keys - required_keys):
            errors.append(f"{rel(path)} unexpected ecosystem profile frontmatter key: {key}")
        for key in sorted(required_keys & actual_keys):
            if not frontmatter[key]:
                errors.append(f"{rel(path)} empty ecosystem profile frontmatter key: {key}")
        if frontmatter.get("profile_id") != path.stem:
            errors.append(f"{rel(path)} profile_id must match filename stem")
        evidence_refs = [item.strip() for item in frontmatter.get("evidence_refs", "").split(";") if item.strip()]
        if not evidence_refs:
            errors.append(f"{rel(path)} evidence_refs must contain at least one pointer")
        if len(evidence_refs) > 6:
            errors.append(f"{rel(path)} evidence_refs must contain at most 6 pointers")
        nonblank_body_lines = [line for line in body.splitlines() if line.strip()]
        if len(nonblank_body_lines) > 12:
            errors.append(f"{rel(path)} body must be at most 12 nonblank lines")

        if filename == "htmlcss-computable-spatial.md":
            for phrase in contains_all(body, [
                "contrast-ratio math",
                ">=4.5:1 for text",
                ">=3:1 for large text",
                ">=3:1 for graphical objects and component states",
                ">=24x24 CSS px",
                "Decidable check",
                "Advisory check",
                "repo-token convention",
            ]):
                errors.append(f"{rel(path)} missing computable spatial profile phrase: {phrase}")
        if filename == "htmlcss-modern-layout.md":
            for phrase in contains_all(body, [
                "CSS grid",
                "flexbox",
                "Container queries",
                "Baseline widely available",
                "Cascade layers",
                "logical properties",
                "`clamp()`",
                "Tailwind v4",
                "`@theme`",
            ]):
                errors.append(f"{rel(path)} missing modern layout profile phrase: {phrase}")
        if filename == "htmlcss-motion-implementation.md":
            for phrase in contains_all(body, [
                "transform and opacity",
                "`prefers-reduced-motion`",
                ".agent-org/knowledge/ui/ui-feel-foundations.md",
                "must not encode fixed constants",
            ]):
                errors.append(f"{rel(path)} missing motion implementation profile phrase: {phrase}")
            if re.search(r"(?<![-/])\b\d+\s*ms\b(?!\s*[-/])", body.lower()):
                errors.append(f"{rel(path)} must not encode fixed ms constants")
    return errors


def check_intake_template() -> list[str]:
    errors: list[str] = []
    path = ROOT / ".agent-org/intake-template.md"
    content = text(path)
    for phrase in contains_all(content, [
        "## Experience Constraints",
        "Required for human-facing deliverables",
        "strategy",
        "scope",
        "structure",
        "frame",
        "presentation",
        "Feel surfaces",
        "proves:",
        "timing-ranges",
        "UI/UX profiles",
        "aufheben escalate-on-missing-section convention",
        "not validator runtime inspection",
        "## design-thesis",
        "## interpretation-scope",
        "## composition acceptance propositions",
    ]):
        errors.append(f"{rel(path)} missing intake phrase: {phrase}")
    return errors


def check_active_directories() -> list[str]:
    errors: list[str] = []
    role_files = sorted(path.stem for path in (ROOT / "roles").glob("*.md"))
    expected_roles = sorted(FINAL_AGENTS + ["controller"])
    if role_files != expected_roles:
        errors.append(f"roles directory must contain only final agents plus controller: {role_files}")
    codex_files = sorted(path.stem for path in (ROOT / ".codex/agents").glob("*.toml"))
    if codex_files != sorted(CODEX_ADAPTERS):
        errors.append(f".codex/agents must contain only expected adapters: {codex_files}")
    claude_files = sorted(path.stem for path in (ROOT / ".claude/agents").glob("*.md"))
    if claude_files != sorted(CLAUDE_ADAPTERS):
        errors.append(f".claude/agents must contain only expected adapters: {claude_files}")
    antigravity_files = sorted(path.name for path in (ROOT / ".antigravity/agents").glob("*.md"))
    if antigravity_files:
        errors.append(f".antigravity/agents must not contain active adapters: {antigravity_files}")
    return errors


def check_controller_role() -> list[str]:
    errors: list[str] = []
    path = ROOT / "roles/controller.md"
    if not path.is_file():
        return [f"missing: {rel(path)}"]
    content = text(path)
    for heading in ROLE_HEADINGS:
        if heading not in content:
            errors.append(f"{rel(path)} missing heading: {heading}")
    for phrase in contains_all(content, [
        "Primary Carrier",
        "None. The controller is not a carrier agent.",
        "invoke",
        "retry",
        "timeout",
        "round-count",
        "escalate-to-human",
        "preference injection",
        "evidence curation",
        "framing",
        "trust-weighting disguised as meta info",
        "content-grounded loop decisions",
        "forwarded verbatim",
        "intake",
        "post-adoption",
        "verbatim transcription of contract-specified text",
        "sandbox cannot write a file",
        "verify findings limited to mechanical fact-checking against repo evidence",
        "no adoption authority",
        "## MERGE GATE",
        "## VERIFICATION BATTERY",
        "scripts/merge-gate.py",
    ]):
        errors.append(f"{rel(path)} missing controller phrase: {phrase}")
    battery = content.split("## VERIFICATION BATTERY", 1)[1] if "## VERIFICATION BATTERY" in content else ""
    instrument_paths = sorted({
        item
        for item in re.findall(r"`([^`]+)`", battery)
        if "/" in item and "<" not in item
    })
    if not instrument_paths:
        errors.append(f"{rel(path)} verification battery must name instrument paths")
    for instrument in instrument_paths:
        candidate = ROOT / instrument.rstrip("/")
        if not candidate.exists():
            errors.append(f"{rel(path)} verification battery instrument missing: {instrument}")
    return errors


def check_roles() -> list[str]:
    errors: list[str] = []
    for agent in FINAL_AGENTS:
        path = ROOT / "roles" / f"{agent}.md"
        if not path.is_file():
            continue
        content = text(path)
        for heading in ROLE_HEADINGS:
            if heading not in content:
                errors.append(f"{rel(path)} missing heading: {heading}")
        schema = SCHEMA_BY_AGENT[agent]
        if schema not in content:
            errors.append(f"{rel(path)} must reference {schema}")
        if "adoption" not in content.lower():
            errors.append(f"{rel(path)} must prohibit adoption claims")
    workflow_agents = [
        "functional-ci-action-writer",
        "security-ci-action-writer",
        "nonfunctional-ci-action-writer",
    ]
    for agent in workflow_agents:
        content = text(ROOT / "roles" / f"{agent}.md")
        for phrase in [".github/workflows/**", "Do not invent commands", "package manifests", "branch protection"]:
            if phrase.lower() not in content.lower():
                errors.append(f"roles/{agent}.md missing CI writer phrase: {phrase}")
    for agent in ["aggressive-designer", "conservative-designer", "genius"]:
        content = text(ROOT / "roles" / f"{agent}.md")
        for phrase in ["Outputs only to `aufheben-designer`", "directly instruct `implementer`"]:
            if phrase.lower() not in content.lower():
                errors.append(f"roles/{agent}.md missing designer boundary: {phrase}")
        if agent in {"aggressive-designer", "conservative-designer"}:
            for phrase in contains_all(content, ["confidence", "evidence pointer"]):
                errors.append(f"roles/{agent}.md missing designer confidence phrase: {phrase}")
        if agent == "aggressive-designer":
            for phrase in contains_all(content, [
                "rejection_conditions",
                "conflict_points",
                "questioning targets",
            ]):
                errors.append(f"roles/{agent}.md missing aggressive phrase: {phrase}")
            if not re.search(r"select.{0,40}(~?3|three)", content, re.IGNORECASE | re.DOTALL):
                errors.append(f"roles/{agent}.md missing aggressive phrase: select near 3")
        if agent == "genius":
            for phrase in ["Output Budget", "32000"]:
                if phrase.lower() not in content.lower():
                    errors.append(f"roles/{agent}.md missing genius budget phrase: {phrase}")
    aufheben_content = text(ROOT / "roles/aufheben-designer.md")
    for phrase in [
        '"proceed"',
        '"redo"',
        '"escalate"',
        "schemas/aufheben-verdict.schema.json",
    ]:
        if phrase.lower() not in aufheben_content.lower():
            errors.append(f"roles/aufheben-designer.md missing aufheben verdict phrase: {phrase}")
    for phrase in contains_all(aufheben_content, [
        "low-confidence convergence",
        "high-confidence convergence",
        "high-confidence disagreement",
        "conflict_points",
    ]):
        errors.append(f"roles/aufheben-designer.md missing confidence quadrant phrase: {phrase}")
    return errors


def check_codex_adapters(toml_data: dict[Path, dict]) -> list[str]:
    errors: list[str] = []
    required_keys = {"name", "description", "model_reasoning_effort", "sandbox_mode", "developer_instructions"}
    for agent in CODEX_ADAPTERS:
        path = ROOT / ".codex/agents" / f"{agent}.toml"
        parsed = toml_data.get(path)
        if parsed is None:
            errors.append(f"{rel(path)} was not parsed")
            continue
        for key in sorted(required_keys - set(parsed)):
            errors.append(f"{rel(path)} missing TOML key: {key}")
        if parsed.get("model_reasoning_effort") != "high":
            errors.append(f"{rel(path)} model_reasoning_effort must be high")
        expected_sandbox = "workspace-write" if agent in {
            "functional-ci-action-writer",
            "nonfunctional-ci-action-writer",
            "implementer",
        } else "read-only"
        if parsed.get("sandbox_mode") != expected_sandbox:
            errors.append(f"{rel(path)} sandbox_mode must be {expected_sandbox}")
        instructions = str(parsed.get("developer_instructions", ""))
        if f"roles/{agent}.md" not in instructions:
            errors.append(f"{rel(path)} must reference roles/{agent}.md")
        if SCHEMA_BY_AGENT[agent] not in instructions:
            errors.append(f"{rel(path)} must reference {SCHEMA_BY_AGENT[agent]}")
        if "No adoption authority" not in instructions:
            errors.append(f"{rel(path)} must state no adoption authority")
        if agent == "conservative-designer":
            for phrase in contains_all(instructions, ["confidence", "evidence pointer"]):
                errors.append(f"{rel(path)} missing designer confidence phrase: {phrase}")
            for phrase in contains_all(instructions, [
                "selected_profiles max 5",
                "version_constraints max 6",
                "ecosystem_facts_used max 8",
                "forbidden_expansions max 6",
                "safe_change_path maxLength 600",
                "reversibility_plan maxLength 600",
                "missing_safety_checks max 6",
                "knowledge_gaps max 6",
                "omit the entire continuity object",
            ]):
                errors.append(f"{rel(path)} missing continuity adapter phrase: {phrase}")
    return errors


def check_claude_adapters() -> list[str]:
    errors: list[str] = []
    required_keys = {"name", "description", "tools", "model", "permissionMode"}
    for agent in CLAUDE_ADAPTERS:
        path = ROOT / ".claude/agents" / f"{agent}.md"
        frontmatter, body, error = parse_frontmatter(path)
        if error:
            errors.append(f"{rel(path)} {error}")
            continue
        for key in sorted(required_keys - set(frontmatter)):
            errors.append(f"{rel(path)} missing frontmatter key: {key}")
        if f"roles/{agent}.md" not in body:
            errors.append(f"{rel(path)} must reference roles/{agent}.md")
        if SCHEMA_BY_AGENT[agent] not in body:
            errors.append(f"{rel(path)} must reference {SCHEMA_BY_AGENT[agent]}")
        if "No adoption authority" not in body:
            errors.append(f"{rel(path)} must state no adoption authority")
        if agent == "aggressive-designer":
            for phrase in contains_all(body, ["confidence", "evidence pointer"]):
                errors.append(f"{rel(path)} missing designer confidence phrase: {phrase}")
            for phrase in contains_all(body, ["rejection_conditions", "conflict_points"]):
                errors.append(f"{rel(path)} missing aggressive phrase: {phrase}")
        if agent == "aufheben-designer":
            for phrase in contains_all(body, [
                "low-confidence convergence",
                "high-confidence convergence",
                "high-confidence disagreement",
            ]):
                errors.append(f"{rel(path)} missing confidence quadrant phrase: {phrase}")
        tools = frontmatter.get("tools", "")
        read_only_agents = {"aggressive-designer", "genius", "aufheben-designer"}
        if agent in read_only_agents and any(tool in tools for tool in ["Bash", "Edit", "Write"]):
            errors.append(f"{rel(path)} read-only agent must not include Bash, Edit, or Write")
        if agent == "security-ci-action-writer" and frontmatter.get("model") != "fable":
            errors.append(f"{rel(path)} model must be fable")
        elif agent != "security-ci-action-writer" and frontmatter.get("model") != "inherit":
            errors.append(f"{rel(path)} model must be inherit")
        if frontmatter.get("model") == "default":
            errors.append(f"{rel(path)} model must not be default")
        if agent == "genius":
            for tool in ["WebSearch", "WebFetch"]:
                if tool not in tools:
                    errors.append(f"{rel(path)} missing external research tool: {tool}")
            if "verification_status" not in body:
                errors.append(f"{rel(path)} must define verification_status behavior")
            if "32000" not in body:
                errors.append(f"{rel(path)} missing genius budget phrase: 32000")
    return errors


def check_evaluation_docs() -> list[str]:
    errors: list[str] = []
    path = ROOT / "docs/evaluation/genius-ab-protocol.md"
    content = text(path)
    for phrase in ["divergence_rate", "forward", "budget_compliance"]:
        if phrase.lower() not in content.lower():
            errors.append(f"{rel(path)} missing evaluation phrase: {phrase}")
    return errors


def check_registry() -> list[str]:
    errors: list[str] = []
    path = ROOT / ".agent-org/runtime-registry.yaml"
    content = text(path)
    for agent in FINAL_AGENTS:
        if f"  {agent}:" not in content:
            errors.append(f"{rel(path)} missing agent: {agent}")
    for phrase in ["protocol:", "codex-main-controller", "subsystems:", "local-tooling", "gate-reporting", "artifact-hashing"]:
        if phrase not in content:
            errors.append(f"{rel(path)} missing registry phrase: {phrase}")
    return errors


def check_pack_policies(toml_data: dict[Path, dict]) -> list[str]:
    errors: list[str] = []

    codex_config = toml_data.get(ROOT / ".codex/config.toml", {})
    if "skills" in codex_config:
        errors.append(".codex/config.toml must not use bare [skills] enabled config")

    carrier = text(ROOT / ".agent-org/carrier-invocation.md")
    for phrase in [
        "codex exec",
        "developer_instructions",
        "--agent \"<agent>\"",
        "cli-output.json",
        "result.json",
        "scripts/extract-claude-result.py",
        "claude_api_unreachable",
        "claude_auth_unavailable",
        "Claude carrier requires network access",
        "structured_output",
        "carrier_output_invalid",
        "Retry with concise JSON only",
        "--allowedTools",
        "--json-schema",
        "< /dev/null",
        "F7 silent hang: 0% CPU, empty stdout",
        "--raw-text",
        "direct parse, then bounded closure repair, then largest-object salvage",
        "invoked command, exit status, sandbox mode, first stderr line on failure, and timeout/fallback status",
    ]:
        if phrase not in carrier:
            errors.append(f".agent-org/carrier-invocation.md missing phrase: {phrase}")
    forbidden_prompt_flag = "--append-system" + "-prompt"
    if forbidden_prompt_flag in carrier:
        errors.append(f".agent-org/carrier-invocation.md must not invoke Claude adapters through {forbidden_prompt_flag}")

    contract_schema = text(ROOT / "schemas/implementation-contract.schema.json")
    if "contract_id" not in contract_schema:
        errors.append("schemas/implementation-contract.schema.json must include contract_id")

    implementer_role = text(ROOT / "roles/implementer.md")
    if "contract_id" not in implementer_role or "implementation_contract_id" not in implementer_role:
        errors.append("roles/implementer.md must map contract_id to implementation_contract_id")

    lifecycle = text(ROOT / ".agent-org/run-lifecycle.md")
    for phrase in [
        "Default carrier execution timeout is 30 minutes",
        "carrier_timeout",
        "Silent hangs are detectable only by timeout",
        "## Resume",
        "Do not redesign. Verify existing work against the original contract. Run required_checks. Emit the required report.",
        "preserve the dead attempt's artifacts unmodified",
        "Stage-A UI/UX SPEC",
        "Stage-B intake",
        "docs-only UI/UX SPEC cycle",
        "CI-constraints rank",
        ".agent-org/intake-template.md",
    ]:
        if phrase not in lifecycle:
            errors.append(f".agent-org/run-lifecycle.md missing phrase: {phrase}")
    for phrase in [
        "MAX 2 redo rounds",
        "redo_brief",
        "redo_max=2 is provisional",
    ]:
        if phrase not in lifecycle:
            errors.append(f".agent-org/run-lifecycle.md missing redo loop phrase: {phrase}")

    bootstrap = text(ROOT / "bootstrap/codex-bootstrap.md")
    for phrase in [
        "Claude CLI is available, authenticated, network-capable",
        "carrier_unavailable",
        "do not retry by guessing a different invocation",
    ]:
        if phrase not in bootstrap:
            errors.append(f"bootstrap/codex-bootstrap.md missing Claude precondition phrase: {phrase}")

    return errors


def check_bootstrap() -> list[str]:
    errors: list[str] = []
    path = ROOT / "bootstrap/codex-bootstrap.md"
    content = text(path)
    for agent in FINAL_AGENTS:
        if agent not in content:
            errors.append(f"{rel(path)} missing agent: {agent}")
    for phrase in [
        "Codex main is the execution controller",
        "delegate the workflow change to the relevant CI action writer",
        "CI constraints must come from",
        "Codex main may add exactly `.agent-runs/`",
        ".github/workflows/**",
        "schemas/implementation-contract.schema.json",
        "schemas/implementation-result.schema.json",
    ]:
        if phrase not in content:
            errors.append(f"{rel(path)} missing phrase: {phrase}")
    return errors


def infer_pack_mode(override: str | None, stamp_exists: bool) -> str:
    if override:
        return override
    return "target" if stamp_exists else "source"


def check_mode_detection_samples() -> list[str]:
    errors: list[str] = []
    cases = [
        (None, False, "source"),
        (None, True, "target"),
        ("source", True, "source"),
        ("target", False, "target"),
    ]
    for override, stamp_exists, expected in cases:
        actual = infer_pack_mode(override, stamp_exists)
        if actual != expected:
            errors.append(f"mode_detection_sample_failed: override={override!r} stamp_exists={stamp_exists!r}")
    return errors


def is_source_repo() -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "remote", "-v"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    if result and SOURCE_REPO_SLUG in result.stdout:
        return True
    return (
        ROOT.name == "ai-org-bootstrap"
        and (ROOT / "docs/evaluation/genius-ab-protocol.md").is_file()
        and (ROOT / "bootstrap/codex-bootstrap.md").is_file()
    )


def check_mode(mode: str, stamp_exists: bool) -> list[str]:
    errors: list[str] = []
    if stamp_exists and (mode == "source" or is_source_repo()):
        errors.append("stamp_in_source_repo: .agent-org/pack-version exists while validating the source pack")
    return errors


def check_pack_stamp(manifest: dict, mode: str, stamp_exists: bool) -> list[str]:
    if mode != "target" or not stamp_exists:
        return []

    loaded, error = load_json(PACK_VERSION)
    if error or not isinstance(loaded, dict):
        return [f"pack_stamp_invalid: .agent-org/pack-version: {error or 'stamp must be object'}"]

    errors: list[str] = []
    for key in ["upstream_commit", "synced_at", "manifest_sha256", "files"]:
        if key not in loaded:
            errors.append(f"pack_stamp_invalid: missing field {key}")
    manifest_hash = sha256_file(PACK_MANIFEST)
    if loaded.get("manifest_sha256") != manifest_hash:
        errors.append("pack_stamp_invalid: manifest_sha256 does not match pack-manifest.json")
    if not isinstance(loaded.get("files"), dict):
        errors.append("pack_stamp_invalid: files must be object")
    elif manifest:
        expected_files = set(manifest_required_files(manifest))
        pack_files = set(manifest_pack_files(manifest))
        stamped_files = set(str(item) for item in loaded["files"])
        missing = sorted(expected_files - stamped_files)
        if missing:
            errors.append(f"pack_stamp_invalid: missing file hashes: {missing}")
        extra = sorted(stamped_files - pack_files)
        if extra:
            errors.append(f"pack_stamp_invalid: non-manifest file hashes: {extra}")
        for stamped_path, stamped_hash in sorted(loaded["files"].items()):
            path_error = invalid_manifest_path(stamped_path)
            if path_error:
                errors.append(f"pack_stamp_invalid: {stamped_path}: {path_error}")
                continue
            if not isinstance(stamped_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", stamped_hash):
                errors.append(f"pack_stamp_invalid: {stamped_path}: sha256 must be lowercase hex")
                continue
            current_path = ROOT / stamped_path
            if not current_path.is_file():
                errors.append(f"pack_stamp_drift: {stamped_path}: missing")
                continue
            current_hash = sha256_file(current_path)
            if current_hash != stamped_hash:
                errors.append(f"pack_stamp_drift: {stamped_path}: sha256 mismatch")
    return errors


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError:
        raise ValidationReadError(path, "missing") from None
    except OSError as exc:
        raise ValidationReadError(path, str(exc)) from None
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the AI Quality Bootstrap pack.")
    parser.add_argument("--schema", help="Schema file for validating one JSON instance.")
    parser.add_argument("--instance", help="JSON instance file to validate against --schema.")
    parser.add_argument("--mode", choices=["source", "target"], help="Override source/target pack validation mode.")
    args = parser.parse_args(argv)

    if args.schema or args.instance:
        if not args.schema or not args.instance:
            print(json.dumps({
                "status": "fail",
                "exit_code": 1,
                "errors": ["--schema and --instance must be provided together"],
            }, indent=2))
            return 1
        return validate_instance_cli(args.schema, args.instance)

    stamp_exists = PACK_VERSION.is_file()
    mode = infer_pack_mode(args.mode, stamp_exists)
    manifest, manifest_errors = load_pack_manifest()

    toml_paths = [ROOT / ".codex/config.toml"] + sorted((ROOT / ".codex/agents").glob("*.toml"))
    toml_data, toml_errors, warnings = load_toml(toml_paths)

    errors: list[str] = []
    errors.extend(manifest_errors)
    errors.extend(check_mode(mode, stamp_exists))
    errors.extend(check_mode_detection_samples())
    if manifest is not None:
        errors.extend(check_pack_manifest_self_test(manifest))
        errors.extend(guarded("check_tool_io_substrate", check_tool_io_substrate))
        errors.extend(check_required_files(manifest))
        errors.extend(guarded("check_manifest_recorded_hashes", check_manifest_recorded_hashes, manifest))
        errors.extend(guarded("check_pack_stamp", check_pack_stamp, manifest, mode, stamp_exists))
        if mode == "source":
            errors.extend(guarded("check_pack_manifest_completeness", check_pack_manifest_completeness, manifest))
            errors.extend(guarded("check_pack_manifest_completeness_negative_fixture", check_pack_manifest_completeness_negative_fixture))
    errors.extend(f"json_parse_error: {item}" for item in guarded("parse_json_files", parse_json_files))
    errors.extend(f"schema_conformance_error: {item}" for item in guarded("check_schema_samples", check_schema_samples))
    errors.extend(guarded("check_linon_review_fixtures", check_linon_review_fixtures))
    errors.extend(guarded("check_linon_packet_fixture", check_linon_packet_fixture))
    errors.extend(f"schema_explicit_type_error: {item}" for item in guarded("check_schema_explicit_types", check_schema_explicit_types))
    errors.extend(f"toml_parse_error: {item}" for item in toml_errors)
    errors.extend(guarded("check_knowledge_cards", check_knowledge_cards))
    errors.extend(guarded("check_ui_profile_cards", check_ui_profile_cards))
    errors.extend(guarded("check_ecosystem_profile_cards", check_ecosystem_profile_cards))
    errors.extend(guarded("check_intake_template", check_intake_template))
    errors.extend(guarded("check_active_directories", check_active_directories))
    errors.extend(guarded("check_controller_role", check_controller_role))
    errors.extend(guarded("check_roles", check_roles))
    errors.extend(guarded("check_codex_adapters", check_codex_adapters, toml_data))
    errors.extend(guarded("check_claude_adapters", check_claude_adapters))
    if mode == "source":
        errors.extend(guarded("check_evaluation_docs", check_evaluation_docs))
    errors.extend(guarded("check_registry", check_registry))
    errors.extend(guarded("check_pack_policies", check_pack_policies, toml_data))
    if mode == "source":
        errors.extend(guarded("check_bootstrap", check_bootstrap))

    payload = {
        "status": "pass" if not errors else "fail",
        "exit_code": 0 if not errors else 1,
        "mode": mode,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
