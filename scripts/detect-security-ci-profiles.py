#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STRING_LIMIT = 200
CAPS = {
    "supporting_profiles": 4,
    "selected_profile_cards": 6,
    "evidence_refs": 12,
    "selection_warnings": 6,
    "security_gaps": 8,
}

PROFILE_TABLE = {
    "workflow:workflow-present": [{"profile_id": "github-actions-general", "priority": 10}],
    "workflow:workflow-permissions-declared": [{"profile_id": "github-actions-permissions", "priority": 12}],
    "workflow:workflow-schedule-declared": [{"profile_id": "scheduled-security-checks", "priority": 18}],
    "workflow:workflow-codeql-named": [{"profile_id": "codeql-analysis", "priority": 14}],
    "workflow:workflow-security-named": [{"profile_id": "security-scan", "priority": 13}],
    "config:gitleaks-ignore": [{"profile_id": "secret-scanning", "priority": 20}],
    "infrastructure:docker-present": [{"profile_id": "container-security", "priority": 30}],
    "infrastructure:iac-present": [{"profile_id": "iac-security", "priority": 30}],
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


def fact_signals(facts: dict) -> list[tuple[str, str]]:
    signals: list[tuple[str, str]] = []
    for item in facts.get("workflow_signals", []):
        if isinstance(item, dict):
            signals.append((f"workflow:{item.get('kind', '')}", clean_string(item.get("path", ""))))
    for item in facts.get("framework_configs", []):
        if isinstance(item, dict):
            signals.append((f"config:{item.get('kind', '')}", clean_string(item.get("path", ""))))
    for item in facts.get("infrastructure_signals", []):
        if isinstance(item, dict):
            signals.append((f"infrastructure:{item.get('kind', '')}", clean_string(item.get("path", ""))))
    return sorted(signals)


def select_profiles(signals: list[tuple[str, str]]) -> tuple[list[str], list[str]]:
    candidates: dict[str, tuple[int, str]] = {}
    evidence: list[str] = []
    for kind, path in signals:
        for row in PROFILE_TABLE.get(kind, []):
            profile_id = row["profile_id"]
            candidate = (int(row["priority"]), profile_id)
            if profile_id not in candidates or candidate < candidates[profile_id]:
                candidates[profile_id] = candidate
            if path:
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
    workflows = facts.get("workflows", [])
    general_enabled = isinstance(workflows, list) and bool(workflows)
    profiles, evidence = select_profiles(fact_signals(facts))
    knowledge_cards = facts.get("knowledge_cards", {}) if isinstance(facts.get("knowledge_cards"), dict) else {}
    pack_cards = list(knowledge_cards.get("pack_security_ci_cards", []))
    selected_cards = matching_cards(pack_cards, profiles)

    if not general_enabled:
        warnings.append("General security CI profile disabled because no .github/workflows files were found.")
    if not pack_cards:
        gaps.append("No security-ci profile cards were found under .agent-org/knowledge/security-ci/.")
    elif not selected_cards:
        gaps.append("Security CI profile card directory has files, but none matched the selected profile ids.")
    output = {
        "evidence_refs": cap(evidence, "evidence_refs", warnings),
        "general_profile_enabled": general_enabled,
        "security_gaps": cap(gaps, "security_gaps", warnings),
        "selected_profile_cards": cap(selected_cards, "selected_profile_cards", warnings),
        "selection_warnings": [],
        "supporting_profiles": cap_ordered(profiles, "supporting_profiles", warnings),
    }
    output["selection_warnings"] = cap(warnings, "selection_warnings", [])
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select security CI profiles from collected repository facts.")
    parser.add_argument("--facts", required=True, help="Facts JSON from collect-repo-evidence.py.")
    parser.add_argument("--output", help="Write selector JSON to this path instead of stdout.")
    args = parser.parse_args(argv)

    payload = json.dumps(detect(facts_from(args.facts)), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
