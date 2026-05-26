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
FLOW_PATH = REPO_ROOT / "study-flows" / "read-the-signal-guided-v0.1.json"


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


def test_load_study_flow_and_flow_helpers():
    flow = op.load_study_flow(FLOW_PATH)
    flows = op.list_study_flows(REPO_ROOT / "study-flows")

    assert flow["kind"] == "openplazma.study_flow"
    assert flow["flowId"] == "read-the-signal-guided-v0.1"
    assert flow["source"]["provider"] == "STATIC_FIXTURE"
    assert flow["source"]["inspiredBy"] == "FAIR_MAST"
    assert flow["capabilities"]["controlFacility"] is False
    assert [item["flowId"] for item in flows] == ["read-the-signal-guided-v0.1"]
    assert op.flow_to_run_config(flow)["studyFlowId"] == "read-the-signal-guided-v0.1"
    assert op.flow_expected_artifacts(flow) == [
        "study_flow",
        "study_task",
        "scenario",
        "experiment_context",
        "signal_series",
        "study_record",
    ]
    assert op.flow_expected_metrics(flow) == [
        "signal_point_count",
        "signal_min",
        "signal_max",
        "signal_mean",
    ]


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


def test_validate_study_flow_rejects_unsafe_capabilities_and_provider():
    flow = op.load_study_flow(FLOW_PATH)
    unsafe = deepcopy(flow)
    unsafe["capabilities"]["controlFacility"] = True
    with pytest.raises(ValueError, match="controlFacility"):
        op.validate_study_flow(unsafe)

    bad_provider = deepcopy(flow)
    bad_provider["source"]["provider"] = "FAIR_MAST"
    with pytest.raises(ValueError, match="STATIC_FIXTURE"):
        op.validate_study_flow(bad_provider)

    inspired = deepcopy(flow)
    inspired["source"]["inspiredBy"] = "FAIR_MAST"
    assert op.validate_study_flow(inspired)["source"]["inspiredBy"] == "FAIR_MAST"


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


def test_read_the_signal_guided_flow_example_runs_and_logs_expected_records(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    env = dict(os.environ)
    env["OPENPLAZMA_RUN_STORE"] = str(run_store)
    completed = subprocess.run(
        [sys.executable, "notebooks/examples/read_the_signal_guided_flow.py"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "OpenPlazma guided StudyFlow run" in completed.stdout
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
    assert artifact_names == [
        "study_flow",
        "study_task",
        "scenario",
        "experiment_context",
        "signal_series",
        "study_record",
    ]

    run_dir = run_store / "runs" / run_id
    combined_output = "\n".join(path.read_text(encoding="utf-8") for path in run_dir.rglob("*") if path.is_file())
    assert '"provider": "FAIR_MAST"' not in combined_output
    study_flow_artifact = run_dir / "artifacts" / "study-flow.json"
    assert study_flow_artifact.is_file()
    assert json.loads(study_flow_artifact.read_text(encoding="utf-8"))["flowId"] == "read-the-signal-guided-v0.1"


def test_guided_study_flow_smoke_script_exports_observatory_compare(tmp_path: Path):
    run_store = tmp_path / ".openplazma"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run-guided-study-flow.py",
            "--run-store",
            str(run_store),
            "--clean",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "OpenPlazma Observatory compare page" in completed.stdout
    runs = op.list_runs(run_store=run_store)
    assert len(runs) == 2
    run_ids = [run["runId"] for run in runs]
    assert run_ids[0] != run_ids[1]
    assert (run_store / "observatory" / "index.html").is_file()
    compare_pages = list((run_store / "observatory" / "compare").glob("*.html"))
    assert len(compare_pages) == 1
    compare_html = compare_pages[0].read_text(encoding="utf-8")
    assert "study_flow::study_flow" in compare_html
    assert "http://" not in compare_html
    assert "https://" not in compare_html
