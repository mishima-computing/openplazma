# %% [markdown]
# # OpenPlazma Experiment Notebook
#
# This notebook template reads a Lab-exported ExperimentContext JSON file,
# loads a STATIC_FIXTURE signal, plots it, and writes a notebook-side
# StudyRecord JSON.

# %%
import openplazma as op

ctx = op.load_experiment_context("notebooks/examples/sample-experiment-context.json")

signal = op.load_static_signal(
    repo_root=".",
    shot_id=ctx["shotRef"]["shotId"],
    signal_id=ctx["signals"][0]["signalId"],
)

op.plot_signal(
    signal,
    time_range=ctx.get("view", {}).get("timeRange"),
)

record = {
    "kind": "openplazma.study_record",
    "version": "0.1.0",
    "studyId": f"{ctx['contextId']}-notebook-study",
    "createdAt": "2026-05-23T00:00:00.000Z",
    "source": {
        "provider": ctx["shotRef"]["provider"],
        "sourceLabel": ctx["source"]["sourceLabel"],
        "inspiredBy": ctx["source"].get("inspiredBy"),
        "shotId": ctx["shotRef"]["shotId"],
    },
    "signalsViewed": ctx["signals"],
    "observations": ctx.get("observations", [])
    + [
        {
            "text": "Notebook analysis reproduced the selected signal from the static fixture."
        }
    ],
    "hypothesis": "This is a notebook-side hypothesis placeholder, not a validated scientific conclusion.",
    "limitations": [
        "This record uses STATIC_FIXTURE data only.",
        "This is not a validated fusion simulation or hardware experiment.",
    ],
}

op.save_study_record(record, "notebooks/examples/sample-study-record-from-notebook.json")

# %% [markdown]
# ## Optional local RunStore logging
#
# This section is for local Python or local Jupyter environments. It writes
# inspectable JSON and JSONL files under `.openplazma/`. The browser
# JupyterLite demo remains STATIC_FIXTURE-only and may not persist local files
# in the same way.

# %%
# with op.start_run(
#     project="openplazma-public-demo",
#     campaign="read-the-signal",
#     run_type="notebook_analysis",
#     context=ctx,
#     config={"source": "notebooks/templates/experiment_notebook.py"},
# ) as run:
#     run.log_artifact("experiment_context", "experiment_context", ctx)
#     run.log_artifact("signal_series", "signal_series", signal)
#     run.log_metric("signal_point_count", len(signal["time"]))
#     run.log_metric("signal_peak", max(signal["values"]))
#     run.log_artifact("study_record", "study_record", record)
