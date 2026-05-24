# Feedback Intake

OpenPlazma feedback is triaged by risk and scope before feature planning.

## First Reviewers

Ask for initial feedback from:

- 1 teacher or science communicator.
- 1 student.
- 1 developer.

## Questions

- Can you open the public demo?
- Can you identify that it uses `STATIC_FIXTURE` data only?
- Can you explain what the signal view appears to show?
- Can you write an observation?
- Can you export a StudyRecord?
- Can you open the Notebook Workbench?
- What was confusing?
- What did you expect next?

## Do Not Ask

- Do not ask users to perform real hardware experiments.
- Do not frame OpenPlazma as a validated simulator.
- Do not frame OpenPlazma as reactor-control software.
- Do not ask for facility-operation feedback from public users.

## Intake Channels

- Bug reports: reproducible Lab, Workbench, build, or documentation failures.
- Demo feedback: public demo clarity, usability, accessibility, and learning flow.
- Scientific scope or safety concerns: provenance, over-strong claims, safety-boundary wording, or anything that could imply real hardware operation.

## Triage Rules

- Keep `STATIC_FIXTURE` provenance explicit.
- Do not treat fixture behavior as validated plasma physics.
- Do not accept real hardware instructions or hazardous experiment procedures.
- Do not request or collect secrets, credentials, private data, or restricted data.
- Do not add external fusion data ingestion through feedback issues.
- Do not add AI assist through feedback issues.

## Labels

- `bug`: reproducible defect or broken workflow.
- `feedback`: public demo feedback that is not a defect.
- `scientific-scope`: concern about claim strength, data provenance, or interpretation.
- `safety`: concern about safety boundary language or out-of-scope hardware behavior.
- `docs`: documentation-only change.
- `future-feature`: future feature idea outside the current public demo.

## Response Pattern

For each issue:

1. Confirm whether the report is in scope for the current `STATIC_FIXTURE` public demo.
2. Ask for reproduction details only when required to act.
3. Keep scientific language limited and explicit.
4. Redirect out-of-scope real hardware or hazardous procedure content to the safety boundary.
5. Close requests for external ingestion, AI assist, or validated simulation behavior as future-scope unless a milestone explicitly includes them.

## Safety-Sensitive Feedback

- Avoid operational details.
- Redirect to safe wording.
- Do not add hazardous instructions.

## Public Demo Acceptance

A public demo feedback item is actionable when it improves one of these without expanding scope:

- The Lab can display the static sample shot and signal.
- The Lab can export or hand off a valid ExperimentContext.
- The Workbench can load the static notebook, context, and signal.
- The UI and docs clearly state the limitations.
- The deployment and smoke checks remain reproducible.
