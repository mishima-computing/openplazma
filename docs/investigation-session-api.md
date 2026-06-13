# Investigation Session API

`InvestigationSession` is the neutral Python API for organizing diagnostic
evidence, conservative assessment state, and evidence-linked reports.

The evidence spine is:

```text
DiagnosticArtifact
  -> ObservationStatement
  -> InvestigationClaim
  -> FusionConditionAssessment
  -> InvestigationReport
  -> RunStore artifacts
```

OpenPlazma does not own the external application's domain state. The external
application converts its own objects into the generic OpenPlazma JSON objects.
OpenPlazma validates evidence references, checks conservative claim boundaries,
assesses measurement gaps, and writes local RunStore artifacts.

This API is local and read-only. It does not perform live network access,
facility telemetry reads, facility control, hosted execution, or source-specific
progression logic.

## Minimum Python Flow

```python
import openplazma as op

package = op.build_investigation_package(
    package_id="external-session-001",
    title="External investigation session",
    target=target,
    questions=questions,
)

session = op.create_investigation_session(
    session_id="session-external-001",
    package=package,
    required_observables=["visible_light", "electric_current", "neutron_flux"],
)

session = op.add_diagnostic_artifact(session, artifact)
session = op.add_observation_statement(session, readout)
session = op.add_investigation_claim(session, claim)

assessment = op.assess_investigation_session(session)
report = op.create_investigation_session_report(session)
session = op.record_investigation_report(session, report)
```

The Python function names are snake_case. Stored JSON keeps the shared
camelCase field names used by the TypeScript schema, such as `packageId`,
`requiredObservables`, `evidenceArtifactIds`, and `nextObservations`.

## Function Roles

- `build_investigation_package(...)` creates an `InvestigationPackage` from a
  target, questions, optional artifacts, optional observations, optional claims,
  and an optional `FusionConditionAssessment`.
- `default_fusion_assessment(package_id)` returns a conservative unresolved
  fusion assessment for draft packages.
- `create_investigation_session(...)` wraps a package with required observables,
  reports, limitations, timestamps, and derived status.
- `add_diagnostic_artifact(session, artifact)` appends one diagnostic artifact.
- `add_observation_statement(session, readout)` appends a mediated readout that
  must cite an existing diagnostic artifact.
- `add_investigation_claim(session, claim)` appends a claim after checking that
  cited diagnostic artifacts exist. Support and contradiction claims are then
  validated through the full package contract.
- `assess_diagnostic_artifact(artifact, required_observables)` reports measured
  observables, calibration state, unresolved contributions, noise or contaminant
  contributions, missing observables, and conservative source-identifiability.
- `assess_investigation_measurements(package, required_observables)` summarizes
  measurement gaps across the package.
- `assess_investigation_session(session)` combines session status and
  measurement assessment state.
- `create_investigation_session_report(session, ...)` creates an
  evidence-linked report from session claims.
- `record_investigation_report(session, report)` appends a report and marks the
  session as `reported`.
- `save_investigation_session(...)` and `load_investigation_session(...)`
  persist and validate session JSON.
- `log_investigation_session(run, session, ...)` writes the session evidence
  set to a local RunStore.

## Status Model

```text
collecting_evidence
  evidence and claims are still incomplete

ready_for_report
  at least one diagnostic artifact and one claim are present

reported
  at least one InvestigationReport is attached
```

`reported` sessions require at least one report. Report `packageId` values must
match the session package, and report claims must cite artifacts and readouts
inside the session package boundary.

## RunStore Artifact Types

`log_investigation_session(run, session)` writes artifacts with stable names and
stable RunStore artifact `type` values:

```text
investigation_package
investigation_session
investigation_assessment
investigation_report
```

The report artifact is written when a report is passed explicitly or when the
session already contains at least one recorded report. The latest session report
is used by default.

Example:

```python
with op.start_run(
    project="openplazma-python-sdk",
    campaign="investigation-session",
    run_type="investigation_session",
    run_store=".openplazma",
) as run:
    artifacts = op.log_investigation_session(run, session)
```

## Executable Example

Run the local example from the repository root:

```sh
python3 scripts/run-investigation-session.py --run-store .openplazma --clean
```

The example builds a generic local session, adds one visible-light artifact, one
mediated readout, one conservative evidence-gap claim, creates a report, and
writes the package, session, assessment, and report to the local RunStore.

## Boundary Rules

- The external application supplies target semantics and converts data into
  `InvestigationTarget`, `DiagnosticArtifact`, `ObservationStatement`, and
  `InvestigationClaim`.
- OpenPlazma does not infer source identity from a single artifact.
- Missing observables remain measurement gaps, not proof of absence.
- Claims keep evidence artifact IDs and mediated readout IDs explicit.
- Reports are JSON artifacts suitable for local storage and inspection.
- The local RunStore path remains inspectable and file-based.
