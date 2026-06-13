#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STRING_LIMIT = 200
CAPS = {
    "primary_ecosystem": 1,
    "supporting_profiles": 4,
    "selected_profile_cards": 5,
    "repo_local_cards": 8,
    "evidence_refs": 12,
    "selection_warnings": 6,
    "knowledge_gaps": 6,
}
ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_CARDS_DIR = ROOT / ".agent-org/knowledge/ecosystems"

PROFILE_TABLE = {
    "manifest:node-package-manifest": [{"profile_id": "node-js", "priority": 10}],
    "manifest:node-npm-lockfile": [{"profile_id": "node-js", "priority": 11}],
    "manifest:node-pnpm-lockfile": [{"profile_id": "node-js", "priority": 12}],
    "manifest:node-yarn-lockfile": [{"profile_id": "node-js", "priority": 13}],
    "manifest:python-project-manifest": [{"profile_id": "python", "priority": 10}],
    "manifest:python-requirements": [{"profile_id": "python", "priority": 11}],
    "manifest:python-poetry-lockfile": [{"profile_id": "python", "priority": 12}],
    "manifest:go-module-manifest": [{"profile_id": "go", "priority": 20}],
    "manifest:rust-cargo-manifest": [{"profile_id": "rust", "priority": 20}],
    "manifest:ruby-bundler-manifest": [{"profile_id": "ruby", "priority": 30}],
    "manifest:php-composer-manifest": [{"profile_id": "php", "priority": 30}],
    "config:nextjs-config": [{"profile_id": "nextjs", "priority": 8}],
    "config:vite-config": [{"profile_id": "vite", "priority": 15}],
    "config:typescript-config": [{"profile_id": "typescript", "priority": 14}],
    "config:pytest-config": [{"profile_id": "python-testing", "priority": 18}],
    "pin:next": [{"profile_id": "nextjs", "priority": 8}],
    "pin:react": [{"profile_id": "react", "priority": 16}],
    "pin:tailwindcss": [
        {"profile_id": "htmlcss-computable-spatial", "priority": 17},
        {"profile_id": "htmlcss-modern-layout", "priority": 18},
        {"profile_id": "htmlcss-motion-implementation", "priority": 19},
    ],
    "runtime:python-version-file": [{"profile_id": "python", "priority": 9}],
    "runtime:node-version-file": [{"profile_id": "node-js", "priority": 9}],
}


def clean_string(value: object) -> str:
    text = " ".join(str(value).strip().split())
    return text[:STRING_LIMIT]


def unique_sorted(values: list[str]) -> list[str]:
    return sorted(dict.fromkeys(clean_string(value) for value in values if clean_string(value)))


def cap(values: list[str], name: str, warnings: list[str]) -> list[str]:
    cleaned = unique_sorted(values)
    limit = CAPS[name]
    if len(cleaned) > limit:
        warnings.append(clean_string(f"{name} truncated from {len(cleaned)} to {limit} items"))
    return cleaned[:limit]


def cap_ordered(values: list[str], name: str, warnings: list[str]) -> list[str]:
    cleaned = list(dict.fromkeys(clean_string(value) for value in values if clean_string(value)))
    limit = CAPS[name]
    if len(cleaned) > limit:
        warnings.append(clean_string(f"{name} truncated from {len(cleaned)} to {limit} items"))
    return cleaned[:limit]


def facts_from(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dependency_pin_signal(pin: object) -> str:
    name, separator, _value = clean_string(pin).partition("=")
    if not separator or "." not in name:
        return ""
    _section, package_name = name.split(".", 1)
    return f"pin:{package_name}" if package_name else ""


def fact_signals(facts: dict) -> list[tuple[str, str]]:
    signals: list[tuple[str, str]] = []
    for item in facts.get("manifests", []):
        if isinstance(item, dict):
            path = clean_string(item.get("path", ""))
            signals.append((f"manifest:{item.get('kind', '')}", path))
            for pin in item.get("version_pins", []):
                signal = dependency_pin_signal(pin)
                if signal:
                    signals.append((signal, clean_string(f"{path}: {pin}")))
    for item in facts.get("framework_configs", []):
        if isinstance(item, dict):
            signals.append((f"config:{item.get('kind', '')}", clean_string(item.get("path", ""))))
    for item in facts.get("runtime_versions", []):
        if isinstance(item, dict):
            signals.append((f"runtime:{item.get('kind', '')}", clean_string(item.get("path", ""))))
    return sorted(signals)


def select_profiles(signals: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    candidates: dict[str, tuple[int, str]] = {}
    evidence: list[str] = []
    for kind, path in signals:
        rows = PROFILE_TABLE.get(kind, [])
        for row in rows:
            profile_id = row["profile_id"]
            candidate = (int(row["priority"]), profile_id)
            if profile_id not in candidates or candidate < candidates[profile_id]:
                candidates[profile_id] = candidate
        if rows and path:
            evidence.append(f"{kind}: {path}")
    profiles = [profile for profile, _ in sorted(candidates.items(), key=lambda item: (item[1][0], item[1][1]))]
    return profiles, evidence


def matching_cards(cards: list[str], profile_ids: list[str]) -> list[str]:
    selected: list[str] = []
    for card in cards:
        basename = Path(card).stem
        if basename in profile_ids:
            selected.append(card)
    return selected


def detect(facts: dict) -> dict:
    warnings: list[str] = []
    gaps: list[str] = []
    profiles, evidence = select_profiles(fact_signals(facts))
    knowledge_cards = facts.get("knowledge_cards", {}) if isinstance(facts.get("knowledge_cards"), dict) else {}
    pack_cards = unique_sorted(
        list(knowledge_cards.get("pack_ecosystem_cards", [])) + list(knowledge_cards.get("pack_domain_cards", []))
    )
    selected_cards = matching_cards(pack_cards, profiles)
    repo_local_cards = list(knowledge_cards.get("repo_local_cards", []))

    if not pack_cards:
        gaps.append("No pack ecosystem/domain profile cards were found under .agent-org/knowledge/ecosystems/ or .agent-org/knowledge/domains/.")
    elif not selected_cards:
        gaps.append("Pack profile card directories have files, but none matched the selected ecosystem profile ids.")
    if not profiles:
        gaps.append("No ecosystem profile signals were detected from manifests, configs, or runtime version files.")

    primary = profiles[:1]
    supporting = profiles[1:]
    output = {
        "evidence_refs": cap(evidence, "evidence_refs", warnings),
        "knowledge_gaps": cap(gaps, "knowledge_gaps", warnings),
        "primary_ecosystem": cap_ordered(primary, "primary_ecosystem", warnings),
        "repo_local_cards": cap(repo_local_cards, "repo_local_cards", warnings),
        "selected_profile_cards": cap(selected_cards, "selected_profile_cards", warnings),
        "selection_warnings": [],
        "supporting_profiles": cap_ordered(supporting, "supporting_profiles", warnings),
    }
    output["selection_warnings"] = cap(warnings, "selection_warnings", [])
    return output


def pack_ecosystem_cards() -> list[str]:
    if not ECOSYSTEM_CARDS_DIR.is_dir():
        return []
    return [
        path.relative_to(ROOT).as_posix()
        for path in sorted(ECOSYSTEM_CARDS_DIR.glob("*.md"))
        if path.name != "README.md"
    ]


def profile_table_ids() -> list[str]:
    profile_ids = [
        str(row["profile_id"])
        for rows in PROFILE_TABLE.values()
        for row in rows
    ]
    return unique_sorted(profile_ids)


def self_test_facts(seed: dict) -> dict:
    payload = dict(seed)
    payload["knowledge_cards"] = {
        "pack_ecosystem_cards": pack_ecosystem_cards(),
        "pack_domain_cards": [],
        "repo_local_cards": [],
    }
    return payload


def run_self_test() -> int:
    expected_cards = {
        "python": ".agent-org/knowledge/ecosystems/python.md",
        "python-testing": ".agent-org/knowledge/ecosystems/python-testing.md",
        "rust": ".agent-org/knowledge/ecosystems/rust.md",
    }
    cases = [
        (
            "rust-cargo-manifest",
            {
                "manifests": [
                    {"kind": "rust-cargo-manifest", "path": "Cargo.toml", "version_pins": []}
                ],
                "framework_configs": [],
                "runtime_versions": [],
            },
            {"rust"},
        ),
        (
            "python-runtime-and-project",
            {
                "manifests": [
                    {"kind": "python-project-manifest", "path": "pyproject.toml", "version_pins": []}
                ],
                "framework_configs": [],
                "runtime_versions": [
                    {"kind": "python-version-file", "path": ".python-version"}
                ],
            },
            {"python"},
        ),
        (
            "pytest-config",
            {
                "manifests": [],
                "framework_configs": [
                    {"kind": "pytest-config", "path": "pytest.ini"}
                ],
                "runtime_versions": [],
            },
            {"python-testing"},
        ),
    ]

    errors: list[str] = []
    for name, facts, expected_profile_ids in cases:
        result = detect(self_test_facts(facts))
        selected = set(result["selected_profile_cards"])
        expected = {expected_cards[profile_id] for profile_id in expected_profile_ids}
        if selected != expected:
            errors.append(
                clean_string(
                    f"{name}: selected_profile_cards expected {sorted(expected)} got {sorted(selected)}"
                )
            )

    card_stems = {Path(card).stem for card in pack_ecosystem_cards()}
    uncarded = [profile_id for profile_id in profile_table_ids() if profile_id not in card_stems]
    payload = {
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "advisory_uncarded_profile_ids": uncarded,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select ecosystem profiles from collected repository facts.")
    parser.add_argument("--facts", help="Facts JSON from collect-repo-evidence.py.")
    parser.add_argument("--output", help="Write selector JSON to this path instead of stdout.")
    parser.add_argument("--self-test", action="store_true", help="Run offline deterministic selector self-test.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()
    if not args.facts:
        parser.error("--facts is required unless --self-test is used")

    payload = json.dumps(detect(facts_from(args.facts)), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
