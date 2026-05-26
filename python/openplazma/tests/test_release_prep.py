from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASES = REPO_ROOT / "docs" / "releases"


def test_release_prep_docs_exist() -> None:
    expected = [
        REPO_ROOT / "docs" / "README.md",
        RELEASES / "0.1-alpha.0.md",
        RELEASES / "0.1-alpha.0-checklist.md",
        RELEASES / "first-reviewer-request.md",
        RELEASES / "one-minute-demo-path.md",
        RELEASES / "0.1-alpha.0-limitations.md",
    ]

    for path in expected:
        assert path.is_file(), f"Missing release prep file: {path}"


def test_release_notes_include_scope_and_do_not_overclaim() -> None:
    release = (RELEASES / "0.1-alpha.0.md").read_text(encoding="utf-8")

    assert "STATIC_FIXTURE" in release
    assert "No public data ingestion" in release
    assert "No AI assist" in release
    assert "No grading or scoring" in release
    assert "Not a real hardware control system" in release
    assert "Teacher / Workshop Pack MVP" in release
    assert "M14: 0.1-alpha.0 Release Execution" in release
    assert "- M13" not in release


def test_release_checklist_and_reviewer_request_are_safe() -> None:
    checklist = (RELEASES / "0.1-alpha.0-checklist.md").read_text(encoding="utf-8")
    reviewer = (RELEASES / "first-reviewer-request.md").read_text(encoding="utf-8")
    limitations = (RELEASES / "0.1-alpha.0-limitations.md").read_text(encoding="utf-8")
    demo_path = (RELEASES / "one-minute-demo-path.md").read_text(encoding="utf-8")

    assert "v0.1-alpha.0" in checklist
    assert "Do not create the release in this PR" in checklist
    assert "https://mishima-computing.github.io/openplazma/" in reviewer
    assert "Please do not send real hardware procedures" in reviewer
    assert "No real hardware instructions" in limitations
    assert "python scripts/run-guided-study-flow.py --run-store .openplazma --clean" in demo_path


def test_no_tracked_release_generated_output() -> None:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "/.openplazma/" not in completed.stdout
    assert not any(line.startswith(".openplazma/") for line in completed.stdout.splitlines())
