# Intake Template

## Experience Constraints

Required for human-facing deliverables. Missing section enforcement is an aufheben escalate-on-missing-section convention, not validator runtime inspection.

## design-thesis

Required for human-facing deliverables. The `design-thesis` must name a positive memorable move that the audience should notice or understand.

Ban-only specs are invalid: a list of things to avoid may constrain execution, but it does not satisfy the design-thesis.

## interpretation-scope

Declare every dimension as `FROZEN` or `FREE`; there is no default. Any undeclared dimension follows the aufheben escalate-on-missing-section convention.

| dimension | state | owner note |
| --- | --- | --- |
| wording | `FROZEN` or `FREE` | Required. |
| structure | `FROZEN` or `FREE` | Required. |
| order | `FROZEN` or `FREE` | Required. |
| staging | `FROZEN` or `FREE` | Required. |
| format | `FROZEN` or `FREE` | Required. |

## composition acceptance propositions

Instantiate named propositions from `ui-composition-patterns` with per-objective thresholds before implementation starts.

Example: `proof-artifact-density-per-view` -> objective threshold, verification artifact, and owner tolerance.

Five layers:

- `strategy`: audience, promise, product posture, and non-goals.
- `scope`: surfaces, flows, states, and excluded interactions.
- `structure`: information architecture, navigation, ordering, and continuity.
- `frame`: layout model, density, affordances, hierarchy, and adaptation.
- `presentation`: copy tone, visual system, motion, audio, haptics, accessibility, and fallback.

Feel surfaces must name cause, state, response, continuity, and recovery when relevant.

Use `proves:` to tie feedback to the exact user-visible state or system fact it confirms.

Use `timing-ranges` rather than fixed constants; product tests or platform guidance pick exact timings.

Name UI/UX profiles explicitly, for example `ui-feel-foundations` or `ui-gacha-genre`. Controllers forward named profiles verbatim; selectors never infer design intent.
