# Run Lifecycle

## Purpose

This policy defines runtime initialization for the final Bootstrap roster.

## Run ID

Generate `run_id` after target repository confirmation:

```text
YYYYMMDD-HHMMSS-<shortsha>
```

Use the current target `HEAD` short SHA for `<shortsha>`.

## Runtime Directory

Initialize:

```text
.agent-runs/<run_id>/
  intake/
  carriers/
  results/
  gates/
  worktrees/
  logs/
```

`.agent-runs/` must remain ignored by Git.

Codex main is responsible for confirming the ignore rule during approved pack materialization. It may add exactly `.agent-runs/` to the target root `.gitignore` if absent.

## Default Sequence

1. Run CI action writer agents when the objective is CI automation.
2. Run designer agents when implementation design is needed.
3. Run `aufheben-designer` to create one implementation contract.
4. Run `implementer` only from that implementation contract.
5. Run deterministic local tooling when configured.
6. Report changed files, commands run, checks, gaps, and remaining work.

Stage-A/Stage-B for UI/UX:

- Stage-A UI/UX SPEC: for human-facing surfaces, run a docs-only UI/UX SPEC cycle and ratify it by merge before implementation cycles.
- Stage-A composition artifact rule: human-facing deliverables SHOULD start comps-first so spatial/register/feel propositions are reviewable before implementation. Decidability exemption: prose spec remains primary when composition propositions are decidable from text; recorded instance HP benchmark 20260612-123650. Comps are mandatory for register or feel-class propositions that remain undecidable in prose. Reviewer pre-filters whichever artifact exists. Rejection condition: after two presentation failures where perceptual grounds were missing, flip that surface class back to comps-first without the exemption until the next ratified lifecycle update.
- Stage-B intake: the ratified spec enters implementation intake at CI-constraints rank.
- Stage-B closeout note: for human-facing surfaces, `scripts/check-spatial.py` is the docs-placed computable spatial lint for overflow/page-widening, fixed-element bounds, opaque-solid contrast, and tap-target advisory review. Deferred follow-ups remain spacing-token modulo after a token-source contract, paint-based contrast #44, safe-area assertions, and CI wiring.
- Stage-B perceptual closeout: for human-facing surfaces, the controller runs `scripts/capture-screens.py` and sends the capture set, spec composition propositions, and exemplar PNG references to `.agent-org/knowledge/ui/perceptual-review-profile.md`. The perceptual reviewer returns absolute per-proposition verdicts plus region-cited findings. First-pass zero-finding reviews trigger controller spot-check; after three consecutive noise-only or no-value spot-check cycles, demote the profile to optional evidence for that surface class.
- Stage-B capture authority: the controller is the sole live-capture executor. Reviewer carriers read emitted PNGs and metadata only; the `capture-metadata.json` field `controller_only_live_capture: true` is the structural check.
- Stage-B Chrome caveat: `scripts/check-spatial.py` does not pass `--user-data-dir` in the live Chrome invocation because new headless already creates an ephemeral profile and Chrome 149, observed 2026-06-12, can hang when `--user-data-dir` is combined with `--headless=new` and `--virtual-time-budget`.
- Experience Constraints live in `.agent-org/intake-template.md`; this lifecycle only orders Stage-A and Stage-B.

Aufheben verdict handling:

- After designers, the controller runs `aufheben-designer`.
- On "proceed", continue with the unchanged implementation contract path.
- On "redo", the controller re-invokes only the named designers with redo_brief appended as input, then re-runs `aufheben-designer`.
- MAX 2 redo rounds.
- If still not "proceed" after 2 rounds, treat as "escalate".
- On "escalate", stop and surface to controller/human.
- Record redo rounds and verdicts in run notes.
- redo_max=2 is provisional, set to gather data; revise when thrash or premature-escalation patterns emerge.

## Gate Profile

Default gate profile:

```text
gate_profile: bootstrap-final-minimal
```

Required mechanical facts:

- git status
- HEAD SHA
- changed files
- forbidden path check

Optional if not configured:

- lint
- typecheck
- tests
- build
- secret scan

Unavailable project-specific checks must be reported as gaps.

## Carrier Execution Timeout

Default carrier execution timeout is 30 minutes of wall-clock time per carrier process.

On expiry, the controller kills the carrier process and records `carrier_timeout` in `carrier-status.json`. Silent hangs are detectable only by timeout; the default may be raised per invocation when the controller expects a legitimately longer run.

## Resume

If a carrier dies or hangs after writing workspace changes but before reporting, preserve the dead attempt's artifacts unmodified and re-invoke the same role with the original file scope and contract.

The resume prompt must be verify-and-report only:

```text
Resume the same role from the existing workspace state. Do not redesign. Verify existing work against the original contract. Run required_checks. Emit the required report.
```

The resumed role must not receive wider file scope than its original contract.

## Closeout

Controller disclosure is a closeout artifact only. `gates/controller-disclosure.json` is written post-verdict/closeout only, never before the `aufheben-designer` verdict, and must disclose each handoff against the leak classes recorded in `roles/controller.md`.

Final report must include:

- run_id
- target repo
- branch
- HEAD SHA
- active agents used
- carrier fallbacks
- changed files
- commands run
- checks passed
- checks failed
- gaps
- warnings
- retry_rate: for runs from this cycle forward, record per-run carrier retry count and cause class for each retry. Cause class is one of `schema_field`, `parse`, `truncation`, or `other`. Historical runs are never recomputed.
- merge_gate_evidence: path to the `scripts/merge-gate.py --out` evidence JSON for any merged pull request.
- `.agent-runs/<run_id>/gates/aufheben-input-embed.json`
- `.agent-runs/<run_id>/gates/controller-disclosure.json` when controller disclosure is written
- controller may distill adopted-cycle facts into `.agent-org/knowledge/cards/` per `.agent-org/knowledge/README.md`
