# Facilitator Guide

## One-Page Summary

Read the Signal is a 45-minute guided session using OpenPlazma's `STATIC_FIXTURE` public demo and optional local workflow. Participants inspect a signal, write an observation, write a hypothesis, and see how local Runs can be inspected with Observatory and Observatory Compare.

## Key Messages

- This is a safe learning workflow using `STATIC_FIXTURE` data.
- Participants are practicing how to observe, record, and compare signal-like data.
- Observation and hypothesis are different: an observation describes what is visible; a hypothesis is a possible explanation.
- RunStore stores local records, artifacts, and metrics.
- Observatory reads local RunStore output and exports static HTML for inspection.
- Observatory Compare compares two local Runs.

## Safe Language To Use

- "This is a safe learning workflow using `STATIC_FIXTURE` data."
- "We are practicing how to observe, record, and compare signal-like data."
- "This is not a validated simulator or hardware control system."
- "The public demo is browser/static and does not inspect local `.openplazma/` files."

## Language To Avoid

- "This controls a plasma device."
- "This predicts real reactor behavior."
- "This is real facility data."
- "Try this on real hardware."

## Explaining STATIC_FIXTURE

`STATIC_FIXTURE` means the data is bundled for a public educational demo. It is stable, local to the project, and safe to inspect. It is not public data ingestion and should not be treated as validated scientific evidence.

## Explaining RunStore And Observatory

Use simple wording:

- Run: one recorded local activity.
- Artifact: a saved input or output from that activity.
- Metric: a small measured summary from that activity.
- RunStore: the local folder that stores those records.
- Observatory: the local static report for reading those records.

## Handling Questions About Real Systems

Keep answers at the boundary:

- OpenPlazma is not a real hardware control system.
- The public demo does not operate facilities, devices, machines, or reactors.
- This workshop does not include real hardware instructions.
- Questions about hazardous procedures are out of scope for this Workshop Pack.

## Collecting Feedback

Use `feedback-form.md`. Do not request private personal data, credentials, secrets, or restricted data.

## Troubleshooting

- If the Lab does not load, use the public smoke checklist.
- If Workbench is slow, continue with the browser-only handout.
- If local setup fails, switch to facilitator demonstration.
- If generated local output is confusing, show only `.openplazma/observatory/index.html`.
