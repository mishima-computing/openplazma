from __future__ import annotations

import os
from pathlib import Path

import openplazma as op


REPO_ROOT = Path(__file__).resolve().parents[2]


def main(run_store: str | Path | None = None) -> str:
    # STATIC_FIXTURE-only, local-only example for Python or local Jupyter use.
    selected_run_store = Path(run_store or os.environ.get("OPENPLAZMA_RUN_STORE", ".openplazma"))
    ctx = op.load_experiment_context(REPO_ROOT / "notebooks" / "examples" / "sample-experiment-context.json")
    signal = op.load_static_signal(
        repo_root=REPO_ROOT,
        shot_id=ctx["shotRef"]["shotId"],
        signal_id=ctx["signals"][0]["signalId"],
    )
    summary = op.summarize_signal(signal)

    observations = [
        {
            "text": "Local notebook workflow inspected the selected STATIC_FIXTURE signal.",
            "signalId": signal["signalId"],
            "timeRange": ctx.get("view", {}).get("timeRange"),
        }
    ]
    record = op.create_study_record(
        context=ctx,
        observations=observations,
        hypothesis="This is a local notebook hypothesis placeholder, not a validated scientific conclusion.",
        study_id=f"{ctx['contextId']}-local-tracking-study",
    )

    with op.start_run(
        project="openplazma-public-demo",
        campaign="read-the-signal",
        run_type="notebook_analysis",
        context=ctx,
        config={"source": "notebooks/examples/local_tracking_notebook.py"},
        run_store=selected_run_store,
    ) as run:
        op.log_context_signal_and_study_record(run, ctx, signal, record)
        run.log_metric("signal_point_count", summary["point_count"])
        run.log_metric("signal_min", summary["min"])
        run.log_metric("signal_max", summary["max"])
        run.log_metric("signal_mean", summary["mean"])
        run_id = run.run_id
        output_path = op.runstore_output_hint(run)

    print(f"OpenPlazma RunStore run {run_id} written to {output_path}")
    return run_id


if __name__ == "__main__":
    main()
