from __future__ import annotations

import os
from pathlib import Path

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_PATH = REPO_ROOT / "study-tasks" / "read-the-signal-static-v0.1.json"


def _prompt_text(task: dict, prompt_type: str) -> str:
    for prompt in task["prompts"]:
        if prompt["type"] == prompt_type:
            return prompt["text"]
    return ""


def main(run_store: str | Path | None = None) -> str:
    # STATIC_FIXTURE-only, local-only StudyTask example for Python or local Jupyter use.
    selected_run_store = Path(run_store or os.environ.get("OPENPLAZMA_RUN_STORE", ".openplazma"))
    task = op.load_study_task(TASK_PATH)
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
    hypothesis = f"{hypothesis_prompt} This remains a local learning hypothesis, not a confirmed conclusion."
    record = op.create_study_record(
        context=ctx,
        observations=observations,
        hypothesis=hypothesis,
        study_id=f"{ctx['contextId']}-{task['taskId']}-study",
        limitations=task["limitations"],
    )

    config = {
        **op.task_to_run_config(task),
        "source": "notebooks/examples/read_the_signal_task.py",
    }

    with op.start_run(
        project="openplazma-public-demo",
        campaign=task["runStoreGuidance"]["campaign"],
        run_type=task["runStoreGuidance"]["runType"],
        context=ctx,
        config=config,
        run_store=selected_run_store,
    ) as run:
        run.log_artifact("study_task", "study_task", task)
        op.log_context_signal_and_study_record(run, ctx, signal, record)
        suggested_metric_names = {metric["name"] for metric in task["suggestedMetrics"]}
        metric_values = {
            "signal_point_count": summary["point_count"],
            "signal_min": summary["min"],
            "signal_max": summary["max"],
            "signal_mean": summary["mean"],
        }
        for name, value in metric_values.items():
            if name in suggested_metric_names:
                run.log_metric(name, value)
        run_id = run.run_id
        output_path = op.runstore_output_hint(run)

    print(f"OpenPlazma StudyTask run {run_id} written to {output_path}")
    return run_id


if __name__ == "__main__":
    main()
