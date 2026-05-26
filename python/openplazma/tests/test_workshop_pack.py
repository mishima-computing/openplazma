from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TEACHER_KIT = REPO_ROOT / "teacher-kit"
WORKSHOP = TEACHER_KIT / "workshops" / "read-the-signal-45min"


def test_read_the_signal_workshop_files_exist() -> None:
    expected = [
        TEACHER_KIT / "README.md",
        WORKSHOP / "README.md",
        WORKSHOP / "facilitator-guide.md",
        WORKSHOP / "participant-handout.md",
        WORKSHOP / "session-plan.md",
        WORKSHOP / "setup-checklist.md",
        WORKSHOP / "safety-and-scope.md",
        WORKSHOP / "feedback-form.md",
        WORKSHOP / "local-technical-appendix.md",
        WORKSHOP / "slide-outline.md",
    ]

    for path in expected:
        assert path.is_file(), f"Missing workshop file: {path}"


def test_workshop_pack_scope_and_commands() -> None:
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    kit_readme = (TEACHER_KIT / "README.md").read_text(encoding="utf-8")
    participant = (WORKSHOP / "participant-handout.md").read_text(encoding="utf-8")
    safety = (WORKSHOP / "safety-and-scope.md").read_text(encoding="utf-8")
    feedback = (WORKSHOP / "feedback-form.md").read_text(encoding="utf-8")
    setup = (WORKSHOP / "setup-checklist.md").read_text(encoding="utf-8")
    appendix = (WORKSHOP / "local-technical-appendix.md").read_text(encoding="utf-8")

    assert "teacher-kit/README.md" in root_readme
    assert "Read the Signal, 45 minutes" in kit_readme
    assert "STATIC_FIXTURE" in participant
    assert "not a validated fusion simulator" in participant
    assert "Not a real hardware control system" in safety
    assert "Do not include credentials, secrets" in feedback
    command = "python scripts/run-guided-study-flow.py --run-store .openplazma --clean"
    assert command in setup
    assert command in appendix
    assert ".openplazma/observatory/index.html" in appendix


def test_no_tracked_workshop_generated_output() -> None:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "/.openplazma/" not in completed.stdout
    assert not any(line.startswith(".openplazma/") for line in completed.stdout.splitlines())
