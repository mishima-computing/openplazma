# Facilitator Guide

## One-page Summary

Read the Signal is a 45-minute Workshop Mission. Participants inspect a `STATIC_FIXTURE` Signal, write one observation, write one hypothesis, and optionally watch or run the local StudyFlow that records Runs and opens Observatory and Compare output. The workshop is read-only decision support: evidence first, conclusions second, no equipment control.

## Key Messages

- This mission uses `STATIC_FIXTURE` data only.
- We are practicing how to observe, record, and compare signal evidence.
- Observation and hypothesis are different.
- A Run is a local record of a workflow.
- Observatory and Compare inspect local records.
- OpenPlazma can support technical judgment, but this workshop does not operate hardware or make standalone safety-critical design decisions.

## Explain The Mission

Use the Mission as a guided path:

1. Enter the Lab.
2. Read the Signal.
3. Write the Logbook.
4. Optionally run the local Mission.
5. Open the Observatory.
6. Compare two Runs.
7. Debrief.

## Explain STATIC_FIXTURE

`STATIC_FIXTURE` means the data is bundled for repeatable public demos.
It is not public data ingestion, live telemetry, or hardware output.

## Explain Observation vs Hypothesis

Observation:

- A statement about what is visible.
- Example shape: "The Signal rises after the start of the chart."

Hypothesis:

- A possible explanation.
- It should remain separate from the observation.

## Explain RunStore Without Jargon

RunStore is the local Logbook storage for Runs.
It saves Run metadata, Metrics, Artifacts, events, and manifests under `.openplazma/`.

## Explain Observatory And Compare

Observatory is a local, static, read-only report for inspecting RunStore output.
Compare is a local, static, read-only page for comparing two Runs.
Neither is hosted, synced, or connected to public data.

## Safe Language To Use

- "This mission uses `STATIC_FIXTURE` data only."
- "We are practicing how to observe, record, and compare signal evidence."
- "This is read-only decision support, not command/control."
- "No operating procedure for a device, reactor, facility, high voltage, vacuum, laser, radiation, or hazardous material is involved."

## Misleading Language To Avoid

- Do not describe the Lab as controlling a device.
- Do not describe the Mission as validating reactor behavior by itself.
- Do not describe fixture records as facility data.
- Do not invite participants to operate hardware from the Mission.
- Do not describe the Mission as having an evaluative outcome.

## Handling Questions About Reactors, Facilities, Or Hardware

Keep answers at the boundary:

- OpenPlazma public demos use `STATIC_FIXTURE` data only.
- The workshop does not provide hardware instructions.
- The workshop does not validate physical behavior by itself.
- OpenPlazma's useful boundary is read-only evidence handling for qualified human review.
- Questions asking for procedures should be redirected to the safety and scope notes.

## Troubleshooting

- If the public demo does not load, refresh and confirm the URL.
- If the Workbench does not open, continue the browser path without it.
- If the local script fails, use the first error message and the setup checklist.
- Do not request credentials, secrets, private data, or restricted data.

## Feedback Collection

Use [feedback-form.md](feedback-form.md).
Focus on clarity, scientific scope, safety wording, and whether the Mission path was understandable.
