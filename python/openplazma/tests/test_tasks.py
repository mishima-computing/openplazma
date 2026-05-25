from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_PATH = REPO_ROOT / "study-tasks" / "read-the-signal-static-v0.1.json"
SCENARIO_PATH = REPO_ROOT / "scenarios" / "read-the-signal.json"


def test_load_study_task_and_scenario():
    task = op.load_study_task(TASK_PATH)
    scenario = op.load_scenario(SCENARIO_PATH)

    assert task["kind"] == "openplazma.study_task"
    assert task["taskId"] == "read-the-signal-static-v0.1"
    assert task["source"]["provider"] == "STATIC_FIXTURE"
    assert task["source"]["inspiredBy"] == "FAIR_MAST"
    assert task["capabilities"]["controlFacility"] is False
    assert scenario["kind"] == "openplazma.scenario"
    assert scenario["taskIds"] == [task["taskId"]]


def test_list_study_tasks_and_task_helpers():
    tasks = op.list_study_tasks(REPO_ROOT / "study-tasks")
    task = tasks[0]

    assert [item["taskId"] for item in tasks] == ["read-the-signal-static-v0.1"]
    assert op.task_default_observations(task) == [
        {
            "text": "What visible change do you notice in the signal?",
        }
    ]
    assert op.task_to_run_config(task)["studyTaskId"] == "read-the-signal-static-v0.1"


def test_validate_study_task_rejects_unsafe_capabilities_and_provider():
    task = op.load_study_task(TASK_PATH)
    unsafe = deepcopy(task)
    unsafe["capabilities"]["controlFacility"] = True
    with pytest.raises(ValueError, match="controlFacility"):
        op.validate_study_task(unsafe)

    bad_provider = deepcopy(task)
    bad_provider["source"]["provider"] = "FAIR_MAST"
    with pytest.raises(ValueError, match="STATIC_FIXTURE"):
        op.validate_study_task(bad_provider)

    inspired = deepcopy(task)
    inspired["source"]["inspiredBy"] = "FAIR_MAST"
    assert op.validate_study_task(inspired)["source"]["inspiredBy"] == "FAIR_MAST"


def test_read_the_signal_task_example_runs_and_logs_expected_records(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    env = dict(os.environ)
    env["OPENPLAZMA_RUN_STORE"] = str(run_store)
    completed = subprocess.run(
        [sys.executable, "notebooks/examples/read_the_signal_task.py"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "OpenPlazma StudyTask run" in completed.stdout
    runs = op.list_runs(run_store=run_store)
    assert len(runs) == 1
    run_id = runs[0]["runId"]
    run_record = op.load_run(run_id, run_store=run_store)
    assert run_record["status"] == "finished"
    assert run_record["source"]["provider"] == "STATIC_FIXTURE"
    assert run_record["capabilities"]["controlFacility"] is False
    assert run_record["capabilities"]["readFacilityTelemetry"] is False

    metrics = op.load_metrics(run_id, run_store=run_store)
    assert [metric["name"] for metric in metrics] == [
        "signal_point_count",
        "signal_min",
        "signal_max",
        "signal_mean",
    ]

    manifest = op.load_manifest(run_id, run_store=run_store)
    artifact_names = [artifact["name"] for artifact in manifest["artifacts"]]
    assert artifact_names == ["study_task", "experiment_context", "signal_series", "study_record"]

    run_dir = run_store / "runs" / run_id
    combined_output = "\n".join(path.read_text(encoding="utf-8") for path in run_dir.rglob("*") if path.is_file())
    assert '"provider": "FAIR_MAST"' not in combined_output
    study_task_artifact = run_dir / "artifacts" / "study-task.json"
    assert study_task_artifact.is_file()
    assert json.loads(study_task_artifact.read_text(encoding="utf-8"))["taskId"] == "read-the-signal-static-v0.1"
