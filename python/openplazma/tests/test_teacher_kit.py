from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
TEACHER_KIT = REPO_ROOT / "teacher-kit"
WORKSHOP = TEACHER_KIT / "workshops" / "read-the-signal-45min"


def test_teacher_kit_files_exist() -> None:
    expected = [
        TEACHER_KIT / "README.md",
        WORKSHOP / "facilitator-guide.md",
        WORKSHOP / "participant-handout.md",
        WORKSHOP / "session-plan.md",
        WORKSHOP / "setup-checklist.md",
        WORKSHOP / "safety-and-scope.md",
        WORKSHOP / "feedback-form.md",
        WORKSHOP / "local-technical-appendix.md",
    ]

    for path in expected:
        assert path.is_file(), f"Missing teacher kit file: {path}"


def test_teacher_kit_scope_language_and_links() -> None:
    readme = (TEACHER_KIT / "README.md").read_text(encoding="utf-8")
    session_plan = (WORKSHOP / "session-plan.md").read_text(encoding="utf-8")
    safety = (WORKSHOP / "safety-and-scope.md").read_text(encoding="utf-8")
    appendix = (WORKSHOP / "local-technical-appendix.md").read_text(encoding="utf-8")
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "https://mishima-computing.github.io/openplazma/" in session_plan
    assert "teacher-kit/README.md" in root_readme
    assert "STATIC_FIXTURE" in readme
    assert "No grading or scoring" in readme
    assert "No public data ingestion" in safety
    assert "No real hardware instructions" in safety
    assert "python scripts/run-guided-study-flow.py --run-store .openplazma --clean" in appendix
    assert ".openplazma/observatory/index.html" in appendix
