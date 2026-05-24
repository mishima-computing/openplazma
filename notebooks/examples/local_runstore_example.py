from __future__ import annotations

from datetime import datetime, timezone

import openplazma as op


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


ctx = op.load_experiment_context("notebooks/examples/sample-experiment-context.json")
signal = op.load_static_signal(
    repo_root=".",
    shot_id=ctx["shotRef"]["shotId"],
    signal_id=ctx["signals"][0]["signalId"],
)

with op.start_run(
    project="openplazma-public-demo",
    campaign="read-the-signal",
    run_type="notebook_analysis",
    context=ctx,
    config={"source": "notebooks/examples/local_runstore_example.py"},
) as run:
    run.log_artifact("experiment_context", "experiment_context", ctx)
    run.log_artifact("signal_series", "signal_series", signal)
    run.log_metric("signal_point_count", len(signal["time"]))
    run.log_metric("signal_peak", max(signal["values"]))

    record = {
        "kind": "openplazma.study_record",
        "version": "0.1.0",
        "studyId": f"{ctx['contextId']}-runstore-example-study",
        "createdAt": now_iso(),
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
                "text": "Local RunStore example logged the selected STATIC_FIXTURE signal."
            }
        ],
        "hypothesis": "This is a local notebook hypothesis placeholder, not a validated scientific conclusion.",
        "limitations": [
            "This record uses STATIC_FIXTURE data only.",
            "This is not a validated fusion simulation or hardware experiment.",
            "This is not a reactor design tool.",
        ],
    }
    op.validate_study_record(record)
    run.log_artifact("study_record", "study_record", record)

print(f"OpenPlazma RunStore run written to .openplazma/runs/{run.run_id}")
