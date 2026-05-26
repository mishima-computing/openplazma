from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TUTORIAL_ROOT = REPO_ROOT / "docs" / "tutorials"
READ_SIGNAL = TUTORIAL_ROOT / "read-the-signal"


def test_read_the_signal_tutorial_files_exist() -> None:
    expected = [
        TUTORIAL_ROOT / "README.md",
        READ_SIGNAL / "README.md",
        READ_SIGNAL / "00-mission-briefing.md",
        READ_SIGNAL / "01-enter-the-lab.md",
        READ_SIGNAL / "02-read-the-signal.md",
        READ_SIGNAL / "03-write-the-logbook.md",
        READ_SIGNAL / "04-run-the-local-mission.md",
        READ_SIGNAL / "05-open-the-observatory.md",
        READ_SIGNAL / "06-compare-two-runs.md",
        READ_SIGNAL / "07-debrief.md",
        READ_SIGNAL / "troubleshooting.md",
        READ_SIGNAL / "glossary.md",
    ]

    for path in expected:
        assert path.is_file(), f"Missing tutorial file: {path}"


def test_tutorial_scope_links_and_mission_language() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    tutorial_index = (TUTORIAL_ROOT / "README.md").read_text(encoding="utf-8")
    mission = (READ_SIGNAL / "README.md").read_text(encoding="utf-8")
    briefing = (READ_SIGNAL / "00-mission-briefing.md").read_text(encoding="utf-8")
    local_mission = (READ_SIGNAL / "04-run-the-local-mission.md").read_text(encoding="utf-8")
    debrief = (READ_SIGNAL / "07-debrief.md").read_text(encoding="utf-8")

    assert "docs/tutorials/README.md" in root_readme
    assert "https://mishima-computing.github.io/openplazma/" in tutorial_index
    assert "STATIC_FIXTURE" in tutorial_index
    assert "No public data ingestion" in tutorial_index
    assert "Mission" in mission
    assert "Mission Checklist" in briefing
    assert "python scripts/run-guided-study-flow.py --run-store .openplazma --clean" in local_mission
    assert ".openplazma/observatory/index.html" in local_mission
    assert "run.json" in local_mission
    assert "metrics.jsonl" in local_mission
    assert "manifest.json" in local_mission
    assert "controlFacility" in local_mission
    assert "What did Compare help you notice?" in debrief


def test_no_tracked_openplazma_generated_output() -> None:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "/.openplazma/" not in completed.stdout
    assert not any(line.startswith(".openplazma/") for line in completed.stdout.splitlines())
