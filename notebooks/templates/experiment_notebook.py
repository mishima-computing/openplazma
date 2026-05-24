# %% [markdown]
# # OpenPlazma Experiment Notebook
#
# This notebook template reads a Lab-exported ExperimentContext JSON file,
# loads a STATIC_FIXTURE SignalSeries, plots it, writes a StudyRecord, and
# can log a complete local RunStore Run in local Python or Jupyter.
#
# The public browser demo remains STATIC_FIXTURE-only and does not require
# persistent local RunStore writes.

# %% [markdown]
# ## 1. Load ExperimentContext

# %%
import openplazma as op

ctx = op.load_experiment_context("notebooks/examples/sample-experiment-context.json")
ctx

# %% [markdown]
# ## 2. Load STATIC_FIXTURE SignalSeries

# %%
signal = op.load_static_signal(
    repo_root=".",
    shot_id=ctx["shotRef"]["shotId"],
    signal_id=ctx["signals"][0]["signalId"],
)
signal["signalId"], len(signal["time"])

# %% [markdown]
# ## 3. Plot Signal

# %%
op.plot_signal(
    signal,
    time_range=ctx.get("view", {}).get("timeRange"),
)

# %% [markdown]
# ## 4. Write Observations And Hypothesis

# %%
observations = [
    {
        "text": "Notebook analysis reproduced the selected signal from the static fixture.",
        "signalId": signal["signalId"],
        "timeRange": ctx.get("view", {}).get("timeRange"),
    }
]

hypothesis = "This is a notebook-side hypothesis placeholder, not a validated scientific conclusion."

# %% [markdown]
# ## 5. Create StudyRecord

# %%
record = op.create_study_record(
    context=ctx,
    observations=observations,
    hypothesis=hypothesis,
    study_id=f"{ctx['contextId']}-notebook-study",
)

op.save_study_record(record, "notebooks/examples/sample-study-record-from-notebook.json")
record

# %% [markdown]
# ## 6. Start Local Run
#
# This section is for local Python or local Jupyter environments. It writes
# inspectable JSON and JSONL files under `.openplazma/`. It does not fetch
# external data, sync to a cloud service, or connect to any external facility.

# %%
summary = op.summarize_signal(signal)

run = op.start_run(
    project="openplazma-public-demo",
    campaign="read-the-signal",
    run_type="notebook_analysis",
    context=ctx,
    config={"source": "notebooks/templates/experiment_notebook.py"},
)

# %% [markdown]
# ## 7. Log Artifacts

# %%
op.log_context_signal_and_study_record(run, ctx, signal, record)

# %% [markdown]
# ## 8. Log Metrics

# %%
run.log_metric("signal_point_count", summary["point_count"])
run.log_metric("signal_min", summary["min"])
run.log_metric("signal_max", summary["max"])
run.log_metric("signal_mean", summary["mean"])

# %% [markdown]
# ## 9. Finish Run

# %%
run.finish()

# %% [markdown]
# ## 10. Inspect Local Output

# %%
print(f"OpenPlazma RunStore run {run.run_id} written to {op.runstore_output_hint(run)}")
