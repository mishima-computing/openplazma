from __future__ import annotations

import os
from pathlib import Path

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[2]
FLOW_PATH = REPO_ROOT / "study-flows" / "read-the-signal-guided-v0.1.json"
TASK_PATH = REPO_ROOT / "study-tasks" / "read-the-signal-static-v0.1.json"
SCENARIO_PATH = REPO_ROOT / "scenarios" / "read-the-signal.json"


def _prompt_text(task: dict, prompt_type: str) -> str:
    for prompt in task["prompts"]:
        if prompt["type"] == prompt_type:
            return prompt["text"]
    return ""


def main(run_store: str | Path | None = None) -> str:
    # STATIC_FIXTURE-only, local-only guided StudyFlow for read-only decision support.
    selected_run_store = Path(run_store or os.environ.get("OPENPLAZMA_RUN_STORE", ".openplazma"))
    flow = op.load_study_flow(FLOW_PATH)
    task = op.load_study_task(TASK_PATH)
    scenario = op.load_scenario(SCENARIO_PATH)

    context_path = REPO_ROOT / task["inputs"]["experimentContextPath"]
    ctx = op.load_experiment_context(context_path)
    signal = op.load_static_signal(
        repo_root=REPO_ROOT,
        shot_id=ctx["shotRef"]["shotId"],
        signal_id=task["inputs"]["signalIds"][0],
    )
    summary = op.summarize_signal(signal)

    observation_prompt = _prompt_text(task, "observation")
    hypothesis_prompt = _prompt_text(task, "hypothesis")
    observations = [
        {
            "text": f"{observation_prompt} The STATIC_FIXTURE signal rises across the selected view.",
            "signalId": signal["signalId"],
            "timeRange": ctx.get("view", {}).get("timeRange"),
        }
    ]
    hypothesis = f"{hypothesis_prompt} This remains a decision-support hypothesis, not a standalone confirmed conclusion."
    record = op.create_study_record(
        context=ctx,
        observations=observations,
        hypothesis=hypothesis,
        study_id=f"{ctx['contextId']}-{flow['flowId']}-study",
        limitations=flow["limitations"],
    )

    config = {
        **op.flow_to_run_config(flow),
        "studyTaskId": task["taskId"],
        "source": "notebooks/examples/read_the_signal_guided_flow.py",
    }

    with op.start_run(
        project="openplazma-public-demo",
        campaign=task["runStoreGuidance"]["campaign"],
        run_type=task["runStoreGuidance"]["runType"],
        context=ctx,
        config=config,
        run_store=selected_run_store,
    ) as run:
        run.log_artifact("study_flow", "study_flow", flow)
        run.log_artifact("study_task", "study_task", task)
        run.log_artifact("scenario", "scenario", scenario)
        op.log_context_signal_and_study_record(run, ctx, signal, record)
        metric_values = {
            "signal_point_count": summary["point_count"],
            "signal_min": summary["min"],
            "signal_max": summary["max"],
            "signal_mean": summary["mean"],
        }
        for name in op.flow_expected_metrics(flow):
            if name in metric_values:
                run.log_metric(name, metric_values[name])
        run_id = run.run_id
        output_path = op.runstore_output_hint(run)

    print(f"OpenPlazma guided StudyFlow run {run_id} written to {output_path}")
    return run_id


if __name__ == "__main__":
    main()
