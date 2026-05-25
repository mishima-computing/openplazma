from __future__ import annotations

from pathlib import Path
from typing import Any

from ._json import load_json
from ._validation import require_keys, require_list, require_mapping, require_string
from .runstore import SAFE_CAPABILITIES


def _validate_source(source: dict[str, Any], label: str) -> dict[str, Any]:
    require_keys(source, ["provider", "sourceLabel"], label)
    if source["provider"] != "STATIC_FIXTURE":
        raise ValueError(f"{label}.provider must be STATIC_FIXTURE.")
    require_string(source["sourceLabel"], f"{label}.sourceLabel")
    if source.get("inspiredBy") is not None and source["inspiredBy"] != "FAIR_MAST":
        raise ValueError(f"{label}.inspiredBy must be FAIR_MAST when provided.")
    return source


def _validate_capabilities(capabilities: dict[str, Any], label: str) -> dict[str, Any]:
    require_keys(capabilities, list(SAFE_CAPABILITIES), label)
    for field, expected in SAFE_CAPABILITIES.items():
        if capabilities[field] is not expected:
            raise ValueError(f"{label}.{field} must be {str(expected).lower()}.")
    return capabilities


def _validate_limitations(limitations: Any, label: str) -> list[Any]:
    values = require_list(limitations, label)
    if not values:
        raise ValueError(f"{label} must include at least one limitation.")
    for index, value in enumerate(values):
        require_string(value, f"{label}[{index}]")
    return values


def validate_study_task(task: dict[str, Any]) -> dict[str, Any]:
    require_keys(
        task,
        [
            "kind",
            "version",
            "taskId",
            "scenarioId",
            "title",
            "summary",
            "level",
            "estimatedMinutes",
            "source",
            "target",
            "capabilities",
            "inputs",
            "learningGoals",
            "prompts",
            "suggestedMetrics",
            "requiredArtifacts",
            "notebookStarter",
            "runStoreGuidance",
            "limitations",
        ],
        "StudyTask",
    )
    if task["kind"] != "openplazma.study_task":
        raise ValueError("StudyTask.kind must be openplazma.study_task.")
    if task["version"] != "0.1.0":
        raise ValueError("StudyTask.version must be 0.1.0.")
    for field in ["taskId", "scenarioId", "title", "summary"]:
        require_string(task[field], f"StudyTask.{field}")
    if task["level"] not in {"beginner", "intermediate", "advanced"}:
        raise ValueError("StudyTask.level must be beginner, intermediate, or advanced.")
    if not isinstance(task["estimatedMinutes"], int) or isinstance(task["estimatedMinutes"], bool) or task["estimatedMinutes"] <= 0:
        raise ValueError("StudyTask.estimatedMinutes must be a positive integer.")

    _validate_source(require_mapping(task["source"], "StudyTask.source"), "StudyTask.source")

    target = require_mapping(task["target"], "StudyTask.target")
    require_keys(target, ["type", "id", "label"], "StudyTask.target")
    if target["type"] != "static_fixture":
        raise ValueError("StudyTask.target.type must be static_fixture.")

    _validate_capabilities(require_mapping(task["capabilities"], "StudyTask.capabilities"), "StudyTask.capabilities")

    inputs = require_mapping(task["inputs"], "StudyTask.inputs")
    require_keys(inputs, ["experimentContextPath", "signalIds"], "StudyTask.inputs")
    require_string(inputs["experimentContextPath"], "StudyTask.inputs.experimentContextPath")
    signal_ids = require_list(inputs["signalIds"], "StudyTask.inputs.signalIds")
    if not signal_ids:
        raise ValueError("StudyTask.inputs.signalIds must include at least one signal id.")
    for index, signal_id in enumerate(signal_ids):
        require_string(signal_id, f"StudyTask.inputs.signalIds[{index}]")

    for field in ["learningGoals", "requiredArtifacts"]:
        values = require_list(task[field], f"StudyTask.{field}")
        if not values:
            raise ValueError(f"StudyTask.{field} must include at least one item.")
        for index, value in enumerate(values):
            require_string(value, f"StudyTask.{field}[{index}]")

    prompts = require_list(task["prompts"], "StudyTask.prompts")
    if not prompts:
        raise ValueError("StudyTask.prompts must include at least one prompt.")
    for index, prompt_ref in enumerate(prompts):
        prompt = require_mapping(prompt_ref, f"StudyTask.prompts[{index}]")
        require_keys(prompt, ["promptId", "type", "text"], f"StudyTask.prompts[{index}]")
        require_string(prompt["promptId"], f"StudyTask.prompts[{index}].promptId")
        if prompt["type"] not in {"observation", "hypothesis", "reflection"}:
            raise ValueError(f"StudyTask.prompts[{index}].type is not supported.")
        require_string(prompt["text"], f"StudyTask.prompts[{index}].text")

    metrics = require_list(task["suggestedMetrics"], "StudyTask.suggestedMetrics")
    if not metrics:
        raise ValueError("StudyTask.suggestedMetrics must include at least one metric.")
    for index, metric_ref in enumerate(metrics):
        metric = require_mapping(metric_ref, f"StudyTask.suggestedMetrics[{index}]")
        require_keys(metric, ["name", "description"], f"StudyTask.suggestedMetrics[{index}]")
        require_string(metric["name"], f"StudyTask.suggestedMetrics[{index}].name")
        require_string(metric["description"], f"StudyTask.suggestedMetrics[{index}].description")

    notebook_starter = require_mapping(task["notebookStarter"], "StudyTask.notebookStarter")
    require_keys(notebook_starter, ["path"], "StudyTask.notebookStarter")
    require_string(notebook_starter["path"], "StudyTask.notebookStarter.path")

    run_guidance = require_mapping(task["runStoreGuidance"], "StudyTask.runStoreGuidance")
    require_keys(run_guidance, ["campaign", "runType"], "StudyTask.runStoreGuidance")
    require_string(run_guidance["campaign"], "StudyTask.runStoreGuidance.campaign")
    require_string(run_guidance["runType"], "StudyTask.runStoreGuidance.runType")

    _validate_limitations(task["limitations"], "StudyTask.limitations")
    return task


def validate_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    require_keys(
        scenario,
        ["kind", "version", "scenarioId", "title", "summary", "level", "taskIds", "limitations"],
        "Scenario",
    )
    if scenario["kind"] != "openplazma.scenario":
        raise ValueError("Scenario.kind must be openplazma.scenario.")
    if scenario["version"] != "0.1.0":
        raise ValueError("Scenario.version must be 0.1.0.")
    for field in ["scenarioId", "title", "summary"]:
        require_string(scenario[field], f"Scenario.{field}")
    if scenario["level"] not in {"beginner", "intermediate", "advanced"}:
        raise ValueError("Scenario.level must be beginner, intermediate, or advanced.")
    task_ids = require_list(scenario["taskIds"], "Scenario.taskIds")
    if not task_ids:
        raise ValueError("Scenario.taskIds must include at least one task id.")
    for index, task_id in enumerate(task_ids):
        require_string(task_id, f"Scenario.taskIds[{index}]")
    _validate_limitations(scenario["limitations"], "Scenario.limitations")
    return scenario


def validate_study_flow(flow: dict[str, Any]) -> dict[str, Any]:
    require_keys(
        flow,
        [
            "kind",
            "version",
            "flowId",
            "title",
            "summary",
            "level",
            "estimatedMinutes",
            "scenarioId",
            "taskIds",
            "source",
            "target",
            "capabilities",
            "steps",
            "expectedArtifacts",
            "expectedMetrics",
            "completionChecklist",
            "limitations",
        ],
        "StudyFlow",
    )
    if flow["kind"] != "openplazma.study_flow":
        raise ValueError("StudyFlow.kind must be openplazma.study_flow.")
    if flow["version"] != "0.1.0":
        raise ValueError("StudyFlow.version must be 0.1.0.")
    for field in ["flowId", "title", "summary", "scenarioId"]:
        require_string(flow[field], f"StudyFlow.{field}")
    if flow["level"] not in {"beginner", "intermediate", "advanced"}:
        raise ValueError("StudyFlow.level must be beginner, intermediate, or advanced.")
    if not isinstance(flow["estimatedMinutes"], int) or isinstance(flow["estimatedMinutes"], bool) or flow["estimatedMinutes"] <= 0:
        raise ValueError("StudyFlow.estimatedMinutes must be a positive integer.")

    task_ids = require_list(flow["taskIds"], "StudyFlow.taskIds")
    if not task_ids:
        raise ValueError("StudyFlow.taskIds must include at least one task id.")
    for index, task_id in enumerate(task_ids):
        require_string(task_id, f"StudyFlow.taskIds[{index}]")

    _validate_source(require_mapping(flow["source"], "StudyFlow.source"), "StudyFlow.source")

    target = require_mapping(flow["target"], "StudyFlow.target")
    require_keys(target, ["type", "id", "label"], "StudyFlow.target")
    if target["type"] != "static_fixture":
        raise ValueError("StudyFlow.target.type must be static_fixture.")

    _validate_capabilities(require_mapping(flow["capabilities"], "StudyFlow.capabilities"), "StudyFlow.capabilities")

    steps = require_list(flow["steps"], "StudyFlow.steps")
    if not steps:
        raise ValueError("StudyFlow.steps must include at least one step.")
    allowed_surfaces = {"lab", "notebook", "runstore", "observatory", "observatory_compare"}
    for index, step_ref in enumerate(steps):
        step = require_mapping(step_ref, f"StudyFlow.steps[{index}]")
        require_keys(step, ["stepId", "title", "surface", "instruction"], f"StudyFlow.steps[{index}]")
        require_string(step["stepId"], f"StudyFlow.steps[{index}].stepId")
        require_string(step["title"], f"StudyFlow.steps[{index}].title")
        if step["surface"] not in allowed_surfaces:
            raise ValueError(f"StudyFlow.steps[{index}].surface is not supported.")
        require_string(step["instruction"], f"StudyFlow.steps[{index}].instruction")

    for field in ["expectedArtifacts", "expectedMetrics", "completionChecklist"]:
        values = require_list(flow[field], f"StudyFlow.{field}")
        if not values:
            raise ValueError(f"StudyFlow.{field} must include at least one item.")
        for index, value in enumerate(values):
            require_string(value, f"StudyFlow.{field}[{index}]")

    _validate_limitations(flow["limitations"], "StudyFlow.limitations")
    return flow


def load_study_task(path: str | Path) -> dict[str, Any]:
    return validate_study_task(load_json(path))


def load_scenario(path: str | Path) -> dict[str, Any]:
    return validate_scenario(load_json(path))


def load_study_flow(path: str | Path) -> dict[str, Any]:
    return validate_study_flow(load_json(path))


def list_study_tasks(root: str | Path = "study-tasks") -> list[dict[str, Any]]:
    selected_root = Path(root)
    manifest = load_json(selected_root / "manifest.json")
    require_keys(manifest, ["kind", "version", "tasks"], "StudyTaskManifest")
    if manifest["kind"] != "openplazma.study_task_manifest":
        raise ValueError("StudyTaskManifest.kind must be openplazma.study_task_manifest.")
    if manifest["version"] != "0.1.0":
        raise ValueError("StudyTaskManifest.version must be 0.1.0.")
    tasks = []
    for index, entry_ref in enumerate(require_list(manifest["tasks"], "StudyTaskManifest.tasks")):
        entry = require_mapping(entry_ref, f"StudyTaskManifest.tasks[{index}]")
        require_keys(entry, ["path"], f"StudyTaskManifest.tasks[{index}]")
        task_path = Path(entry["path"])
        if not task_path.is_absolute():
            task_path = selected_root.parent / task_path
        tasks.append(load_study_task(task_path))
    return tasks


def list_study_flows(root: str | Path = "study-flows") -> list[dict[str, Any]]:
    selected_root = Path(root)
    manifest = load_json(selected_root / "manifest.json")
    require_keys(manifest, ["kind", "version", "flows"], "StudyFlowManifest")
    if manifest["kind"] != "openplazma.study_flow_manifest":
        raise ValueError("StudyFlowManifest.kind must be openplazma.study_flow_manifest.")
    if manifest["version"] != "0.1.0":
        raise ValueError("StudyFlowManifest.version must be 0.1.0.")
    flows = []
    for index, entry_ref in enumerate(require_list(manifest["flows"], "StudyFlowManifest.flows")):
        entry = require_mapping(entry_ref, f"StudyFlowManifest.flows[{index}]")
        require_keys(entry, ["path"], f"StudyFlowManifest.flows[{index}]")
        flow_path = Path(entry["path"])
        if not flow_path.is_absolute():
            flow_path = selected_root.parent / flow_path
        flows.append(load_study_flow(flow_path))
    return flows


def task_default_observations(task: dict[str, Any]) -> list[dict[str, Any]]:
    validated = validate_study_task(task)
    return [{"text": prompt["text"]} for prompt in validated["prompts"] if prompt["type"] == "observation"]


def task_to_run_config(task: dict[str, Any]) -> dict[str, Any]:
    validated = validate_study_task(task)
    return {
        "studyTaskId": validated["taskId"],
        "scenarioId": validated["scenarioId"],
        "title": validated["title"],
        "source": "study_task",
    }


def flow_to_run_config(flow: dict[str, Any]) -> dict[str, Any]:
    validated = validate_study_flow(flow)
    return {
        "studyFlowId": validated["flowId"],
        "scenarioId": validated["scenarioId"],
        "taskIds": validated["taskIds"],
        "title": validated["title"],
        "source": "study_flow",
    }


def flow_expected_metrics(flow: dict[str, Any]) -> list[str]:
    return list(validate_study_flow(flow)["expectedMetrics"])


def flow_expected_artifacts(flow: dict[str, Any]) -> list[str]:
    return list(validate_study_flow(flow)["expectedArtifacts"])
