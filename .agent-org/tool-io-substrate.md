# Tool I/O Substrate

Status: org-internal registry, manifest-listed.

This registry defines the tool I/O substrate for LLM-facing scripts in this
pack. Existing script behavior is canonical-as-shipped unless a row below names
a migration note and supersede trigger. No shipped exit code is renumbered by
this document.

## 1. Stdout Envelope

LLM-facing scripts that print machine output to stdout SHOULD use this compact
JSON envelope:

| Key | Required | Meaning |
| --- | --- | --- |
| `status` | yes | Stable status string derived from the process outcome. |
| `exit_code` | yes | Mirror of the process exit code. |
| `payload` or `pointer` | one | Inline bounded payload, or a run-directory artifact pointer. |
| `summary` | yes for large payloads | Bounded human summary of omitted or pointed content. |

Envelope pointers MUST be relative paths under `.agent-runs/<run>/...`.
Absolute paths, repository-external paths, and paths that escape the run
directory are forbidden for pointer fields.

`scripts/check-anchor-urls.py` is the local exemplar for `status` plus
`exit_code`. Future scripts that need finer branching SHOULD include a JSON
subclass key such as `gate_class`, following `scripts/merge-gate.py`.

## 2. Artifact Vs Stdout Split

Stdout is for compact status and routing data. Large, repeated, or inspectable
outputs SHOULD be written as artifacts under `.agent-runs/<run>/...`; stdout
then returns a pointer and a bounded summary.

Rationale anchors:

| Anchor | Date pin | Use here |
| --- | --- | --- |
| Anthropic Claude Code default output ceiling | 2025-09-11 | Ceiling rationale for keeping stdout bounded; not an org hard token cap. |
| MCP code-exec result, 98.7% | 2025-11-04 | Rationale for preferring structured, extractable tool outputs when available. |
| Tool-output compatibility review | 2025-11-24 | Re-check trigger for envelope and pointer assumptions. |

Scope note: this pointer rule does not alter aufheben verbatim byte-containment
requirements and does not change `scripts/hash-artifacts.py --verify-embed`.
Verbatim embed versus pointer metering remains deferred to the named future
metering trigger.

## 3. Validation Error Shape

Validation errors emitted for repair loops SHOULD be objects with exactly these
keys:

| Key | Meaning |
| --- | --- |
| `field_path` | JSONPath-like path or CLI field name. |
| `actual` | Compact observed value, error text, or absence marker. |
| `allowed` | Compact allowed value, schema rule, or containment rule. |
| `repair_hint` | Concise instruction for the next attempt. |

The shape follows the Instructor reask pattern, accessed 2026-06-12. Repair
hints must stay concise enough to preserve output-cap headroom.

## 4. Exit-Code Class Registry

The coarse classes are frozen:

| Exit code | Class | Meaning |
| --- | --- | --- |
| 0 | pass | Completed successfully. |
| 1 | blocking-fail | Completed and found a blocking failure. |
| 2 | env-or-usage | Could not evaluate because usage, environment, schema, transport, or dependency failed. |
| 3 | qualified-non-failure | Completed or waited into a non-pass state that is not a blocking failure. |

Fine semantics belong in JSON subclass keys, for example `gate_class` in
`scripts/merge-gate.py`. Future scripts SHOULD provide such a key when a
controller needs to distinguish multiple meanings inside one coarse class.

## 5. Self-Test And Fixture Conventions

Both patterns conform:

| Pattern | Conforming use |
| --- | --- |
| `--self-test` | Default for new executable scripts; tests are offline and exit 0 on green. |
| `fixtures/` tree | Conforming for larger reusable fixtures; no relocation is required. |
| Embedded self-test data | Conforming for small fixtures local to one script. |

New executable Python scripts under `scripts/` SHOULD declare `--self-test`
unless they are module-only helpers or have a documented migration note in the
audit table. SWE-agent self-test practice was reviewed as an anchor, accessed
2026-06-12.

## 6. Run-Boundary Declaration

Each script is either controller-run, carrier-run, or shared helper code.
Controller-run scripts may read and write repository-local run artifacts as
directed by the controller. Carrier-run scripts must stay within the carrier
permission surface. Shared helper modules do not define their own process
boundary.

## Read-Only Artifact Submission Ruling

Controller-mediated extract-then-validate is canonical for read-only Claude
roles. Read-only Claude roles MUST NOT receive Bash, Edit, or Write tools for
artifact submission. This restates the recorded #37 gate outcome in
`.agent-org/carrier-invocation.md`; it does not re-decide that gate.

`scripts/submit-result.py` remains scoped to write-capable carriers and
controller-side validation. No substrate text authorizes carriers to self-submit
through shell access.

Supersede trigger: MCP `outputSchema` class submission in carrier CLIs, named
against MCP revision 2025-06-18.

Rejection conditions for the current ruling:

| Condition | Action |
| --- | --- |
| More than 2 extraction failures per 10 read-only runs after repair-shape adoption | Reopen the submission path. |
| Genuine multi-file or over-cap artifact need appears for a read-only role | Reopen the submission path. |
| MCP `outputSchema`-class submission ships in the carrier CLI | Supersede extract-then-validate with the structured output path. |

## Script Audit

| Script | Run boundary | Self-test | Stdout / artifact status | Exit-code class status | Migration note | Supersede trigger |
| --- | --- | --- | --- | --- | --- | --- |
| `build-pages-site.py` | controller-run | no `--self-test`; project-local legacy script | human progress stdout; build artifacts under `dist/` | subprocess failures propagate; success exits 0 | Add envelope only if controller automation consumes it | Next pages build automation change |
| `capture-screens.py` | controller-run | `--self-test` | conforming envelope; artifacts under requested output dir | conforming 0/1/2 | None | New capture contract |
| `check-anchor-urls.py` | controller-run | `--self-test` | conforming `status` + `exit_code` exemplar | deviation: exit 3 is bot-block qualified non-failure | Keep 3=bot-block canonical-as-shipped; use subclass if controllers branch on it | New anchor checker major version |
| `check-public-repo-hygiene.py` | controller-run | no `--self-test`; project-local legacy script | human-readable pass/fail stdout | conforming 0/1 | Add envelope if used by agent merge gate | Next hygiene checker behavior change |
| `check-spatial.py` | controller-run | `--self-test` | conforming envelope; stderr diagnostics on env/schema errors | deviation: exit 2 conflates env-unavailable and schema-error; exit 3 is advisory | Preserve conflation; future scripts add subclass key for env vs schema | Behavioral re-validation cycle |
| `chrome_capture.py` | shared helper | no `--self-test`; module-only helper | no process stdout | no process exit registry | Module-only helper exception | If made executable |
| `collect-repo-evidence.py` | controller-run | no `--self-test`; legacy script | conforming stdout facts JSON | conforming 0/1 | Add offline self-test when script behavior changes | Next evidence collector change |
| `detect-ecosystem-profiles.py` | controller-run | no `--self-test`; legacy script | conforming stdout selector JSON or artifact write | conforming 0 | Add offline self-test when script behavior changes | Next selector change |
| `detect-security-ci-profiles.py` | controller-run | no `--self-test`; legacy script | conforming stdout selector JSON or artifact write | conforming 0 | Add offline self-test when script behavior changes | Next selector change |
| `export-observatory.py` | controller-run | no `--self-test`; project-local legacy script | human-readable output path stdout; errors to stderr | conforming 0/1 | Add envelope if Observatory export becomes merge-gated | Next Observatory export CLI change |
| `extract-claude-result.py` | controller-run | `--self-test` | conforming compact stdout/stderr status | conforming 0/1 | Consider adding `exit_code` mirror in a future cheap-change cycle | Next extractor envelope cycle |
| `fetch-noaa-swpc-real-fixture.py` | controller-run | no `--self-test`; project-local network-fetch script | writes fixture files; human-readable stdout | conforming 0 on success; exceptions fail nonzero | Keep manual/network use explicit; add offline fixture self-test if behavior changes | Next NOAA fixture fetcher change |
| `hash-artifacts.py` | controller-run | no `--self-test`; legacy script | conforming after additive `status` + `exit_code`; `--verify-embed` unchanged | conforming 0/1 | Add offline self-test when hash behavior changes | Next hash tool change |
| `merge-gate.py` | controller-run | `--self-test` | deviation: usage and gh errors are emitted to stderr | conforming; exit 3 is pending/indeterminate | Preserve stderr error channel; use `gate_class` as subclass exemplar | New merge-gate major version |
| `prepare-workbench-lite.py` | controller-run | no `--self-test`; project-local legacy script | human-readable changed/no-change stdout | conforming 0; exceptions fail nonzero | Add idempotence self-test when script behavior changes | Next Workbench Lite preparation change |
| `run-investigation-session.py` | controller-run | no `--self-test`; project-local legacy script | human-readable RunStore path stdout | conforming 0; exceptions fail nonzero | Add offline self-test when script behavior changes | Next investigation session runner change |
| `run-guided-study-flow.py` | controller-run | no `--self-test`; project-local legacy script | human-readable RunStore and Observatory paths stdout | conforming 0; exceptions fail nonzero | Add envelope if used by automated smoke gate | Next guided flow runner change |
| `submit-result.py` | controller-run or write-capable carrier-run | `--self-test` | conforming local-v1 status with repair-shaped errors | conforming 0/1 | Scoped away from read-only carriers | MCP outputSchema carrier submission |
| `sync-pack.py` | controller-run | no `--self-test`; legacy script | conforming status payload | conforming 0/1 | Add offline self-test when sync behavior changes | Next sync-pack behavior change |
| `validate-bootstrap-pack.py` | controller-run | no `--self-test`; validator exercised by required checks | conforming after additive `exit_code` mirror | conforming 0/1 | Add dedicated self-test only if validator harness is split | Validator test harness split |
| `validate-investigation-fixtures.py` | controller-run | no `--self-test`; project-local legacy script | human-readable validation count stdout | conforming 0/1 via validation exceptions | Add envelope only if called by agent merge gate | Next investigation fixture validator change |
