from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TUTORIAL_ROOT = REPO_ROOT / "docs" / "tutorials"
READ_SIGNAL = TUTORIAL_ROOT / "read-the-signal"


def test_read_the_signal_tutorial_files_exist() -> None:
    expected = [
        TUTORIAL_ROOT / "README.md",
        TUTORIAL_ROOT / "investigate-will-o-wisp.md",
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
    investigation = (TUTORIAL_ROOT / "investigate-will-o-wisp.md").read_text(encoding="utf-8")
    mission = (READ_SIGNAL / "README.md").read_text(encoding="utf-8")
    briefing = (READ_SIGNAL / "00-mission-briefing.md").read_text(encoding="utf-8")
    local_mission = (READ_SIGNAL / "04-run-the-local-mission.md").read_text(encoding="utf-8")
    debrief = (READ_SIGNAL / "07-debrief.md").read_text(encoding="utf-8")

    assert "docs/tutorials/README.md" in root_readme
    assert "docs/tutorials/investigate-will-o-wisp.md" in root_readme
    assert "python scripts/validate-investigation-fixtures.py" in root_readme
    assert "https://mishima-computing.github.io/openplazma/" in tutorial_index
    assert "STATIC_FIXTURE" in tutorial_index
    assert "No public data ingestion" in tutorial_index
    assert "Investigate Will-o'-the-wisp" in tutorial_index
    assert "will-o-wisp-001" in investigation
    assert "op.create_investigation_report" in investigation
    assert "python scripts/validate-investigation-fixtures.py" in investigation
    assert "Mission" in mission
    assert "Mission Checklist" in briefing
    assert "python scripts/run-guided-study-flow.py --run-store .openplazma --clean" in local_mission
    assert ".openplazma/observatory/index.html" in local_mission
    assert "run.json" in local_mission
    assert "metrics.jsonl" in local_mission
    assert "manifest.json" in local_mission
    assert "controlFacility" in local_mission
    assert "What did Compare help you notice?" in debrief


def test_will_o_wisp_investigation_example_writes_report(tmp_path) -> None:
    path = REPO_ROOT / "notebooks" / "examples" / "will_o_wisp_investigation_report.py"
    spec = importlib.util.spec_from_file_location("openplazma_will_o_wisp_investigation_report", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output = module.main(output_dir=tmp_path)

    assert output == tmp_path / "will-o-wisp-001-investigation-report.json"
    assert output.read_text(encoding="utf-8").startswith('{\n  "kind": "openplazma.investigation_report"')


def test_validate_investigation_fixtures_script_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validate-investigation-fixtures.py"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "static investigation package" in completed.stdout


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
