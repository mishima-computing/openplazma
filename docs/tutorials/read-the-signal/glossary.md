# Glossary

STATIC_FIXTURE:
A bundled public learning data source used by the demo.

ExperimentContext:
The record that carries Lab selection and context into the Notebook workflow.

SignalSeries:
A signal record with time values and measured-like values for inspection.

StudyRecord:
A human Logbook artifact containing observations, hypothesis text, limitations, and context.

StudyTask:
A concrete learning task with prompts, suggested Metrics, required Artifacts, and limitations.

Scenario:
A named learning context that can contain StudyTasks.

StudyFlow:
An ordered mission path through Lab, Notebook, RunStore, Observatory, and Compare.

Run:
A tracked local activity.

RunStore:
The local inspectable folder that stores RunRecords, Metrics, Artifacts, events, and manifests.

Metric:
A numeric or structured summary logged during a Run.

Artifact:
A saved input or output from a Run.

Observatory:
A local static read-only report for inspecting RunStore output.

Compare:
A local static page for comparing two Runs.

Capability:
Safety and boundary metadata describing what a Run is allowed to do.

Observation:
A statement about what is visible or recorded.

Hypothesis:
A possible explanation, kept separate from the observation.
