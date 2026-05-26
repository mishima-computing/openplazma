# First Reviewer Request

Use these short messages when asking early reviewers to try OpenPlazma `0.1-alpha.0`.

Public demo:

```text
https://mishima-computing.github.io/openplazma/
```

## A. Teacher Or Science Communicator Reviewer

Could you review the Read the Signal Tutorial and Teacher / Workshop Pack?

Please try:

- Open the public demo.
- Follow the browser mission path.
- Read the 45-minute Workshop Pack.
- If you have time, skim the local technical path.

Feedback requested:

- Could you open it?
- Did the mission-style tutorial make sense?
- Could you tell it was `STATIC_FIXTURE`-only?
- Could you distinguish observation from hypothesis?
- Would the Workshop Pack support a 45-minute guided session?
- What was confusing?
- Did any wording seem misleading or unsafe?

Please do not evaluate grading, scoring, public data ingestion, cloud sync, AI assist, or real hardware workflows. Those are not included.

## B. Student Or First-Time User

Could you try the Read the Signal Tutorial as a first-time user?

Please try:

- Open the public demo.
- Find the `STATIC_FIXTURE` Signal.
- Write one observation.
- Write one hypothesis.
- Read the Debrief questions.

Feedback requested:

- Could you open it?
- Did the mission path make sense?
- Could you tell it used `STATIC_FIXTURE` data only?
- Could you tell observation and hypothesis apart?
- What was confusing?
- What would you want explained next?

Please do not try to use OpenPlazma with real hardware or external data.

## C. Developer Reviewer

Could you review the local technical workflow?

Please try:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

Then inspect:

- `.openplazma/runs/...`
- `.openplazma/observatory/index.html`
- `.openplazma/observatory/compare/...`

Feedback requested:

- Did the local RunStore / Observatory / Compare path make sense?
- Were the generated files easy to inspect?
- Did generated output stay under `.openplazma/`?
- Were the docs accurate?
- Did any safety or scope language seem unclear?

Please do not add credentials, secrets, external data, or cloud services.

## D. Scientific Or Domain Reviewer

Could you review the language and scope boundaries?

Please try:

- Open the public demo.
- Read the release notes draft.
- Read the safety and scope notes in the Tutorial and Workshop Pack.
- Skim the RunStore and Observatory docs if useful.

Feedback requested:

- Is the `STATIC_FIXTURE` boundary clear?
- Is observation separated from hypothesis?
- Does any wording imply validated simulation?
- Does any wording imply real hardware control?
- Does any wording imply public data ingestion?
- What should be clarified before broader review?

Please do not send real hardware procedures, restricted data, credentials, or secrets.
