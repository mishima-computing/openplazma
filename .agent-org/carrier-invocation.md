# Carrier Invocation

## Purpose

This policy defines carrier-specific invocation without turning carriers into agents.

Canonical agent behavior lives in `roles/*.md`. Carrier adapters translate that behavior for Codex or Claude Code.

## Codex Invocation

Use `.codex/agents/*.toml` when available.

Codex read-only agents must use read-only tool access.

Codex write-capable agents must use workspace-write access only for the scope allowed by their role and input contract.

Warning: `codex exec` waits on an open non-tty stdin even when a prompt argument is given (F7 silent hang: 0% CPU, empty stdout).

Codex output should be captured under:

```text
.agent-runs/<run_id>/carriers/codex/<agent>/
  input.md
  result.json
  stderr.log
  carrier-status.json
```

Codex `exec` does not directly select project custom agents as a persona. The invocation input must therefore include the matching `.codex/agents/<agent>.toml` `developer_instructions`, canonical `roles/<agent>.md`, schema path, objective, allowed files, forbidden files, and expected output path.

Read-only invocation template:

```bash
codex exec \
  -C "<target_repo_root>" \
  --sandbox read-only \
  --output-schema "schemas/<schema>.schema.json" \
  -o ".agent-runs/<run_id>/carriers/codex/<agent>/result.json" \
  "$(cat .agent-runs/<run_id>/carriers/codex/<agent>/input.md)" \
  2> ".agent-runs/<run_id>/carriers/codex/<agent>/stderr.log" \
  < /dev/null
```

Write-capable invocation template:

```bash
codex exec \
  -C "<target_repo_root>" \
  --sandbox workspace-write \
  --output-schema "schemas/<schema>.schema.json" \
  -o ".agent-runs/<run_id>/carriers/codex/<agent>/result.json" \
  "$(cat .agent-runs/<run_id>/carriers/codex/<agent>/input.md)" \
  2> ".agent-runs/<run_id>/carriers/codex/<agent>/stderr.log" \
  < /dev/null
```

Then validate:

```bash
python3 scripts/validate-bootstrap-pack.py \
  --schema "schemas/<schema>.schema.json" \
  --instance ".agent-runs/<run_id>/carriers/codex/<agent>/result.json"
```

Codex `--output-schema` requires every property schema that declares `const` or `enum` to also declare an explicit `type`, because OpenAI structured_output validation rejects typeless const/enum properties. If `--output-schema` fails before model execution, for example with HTTP 400, re-run without `--output-schema`, instruct final-message-JSON-only output, and validate the captured result post-hoc with `python3 scripts/validate-bootstrap-pack.py --schema "schemas/<schema>.schema.json" --instance ".agent-runs/<run_id>/carriers/codex/<agent>/result.json"`.

### F12 Optional-Property Schema Shape

For any role schema where `properties` contains keys omitted from `required`, such as `schemas/design-proposal.schema.json`, the primary Codex route is no `--output-schema`. Invoke `codex exec` with the same sandbox, target directory, input, output path, stderr capture, and `< /dev/null`, but omit the `--output-schema "schemas/<schema>.schema.json"` argument.

The result must still be JSON-only and must pass mandatory post-hoc validation:

```bash
python3 scripts/validate-bootstrap-pack.py \
  --schema "schemas/<schema>.schema.json" \
  --instance ".agent-runs/<run_id>/carriers/codex/<agent>/result.json"
```

Do not rewrite schemas into null-union form to satisfy structured output. The schema file remains the source of truth; the no `--output-schema` route only avoids a carrier-side schema-shape rejection before model execution.

Codex `carrier-status.json` must record the invoked command, exit status, sandbox mode, first stderr line on failure, and timeout/fallback status. Do not capture tokens, credentials, or the full environment.

If the Codex `-o result.json` file fails JSON parse or schema validation, run `scripts/extract-claude-result.py --raw-text ".agent-runs/<run_id>/carriers/codex/<agent>/result.json" --out ".agent-runs/<run_id>/carriers/codex/<agent>/result.json"` before any carrier retry. The raw-text fallback uses the same pipeline as Claude string results: direct parse, then bounded closure repair, then largest-object salvage. The extracted result must still pass schema validation.

## Claude Code Invocation

Before invoking Claude Code, create:

```text
.agent-runs/<run_id>/carriers/claude/<agent>/
  input.md
  cli-output.json
  result.json
  stderr.log
  carrier-status.json
```

`input.md` must include the objective, selected role spec path, adapter path, schema path, allowed files, forbidden files, expected output path, and this output rule:

```text
Return pure JSON conforming to the schema. Do not wrap it in Markdown, code fences, or explanatory text.
```

Claude role inputs MUST also include this template text:

```text
Drop any key not present in the schema instead of adding tombstone or explanatory fields for removed keys.
```

Deletion condition: remove the drop-the-key sentence only after 3 consecutive clean submit-result Claude-path runs with zero schema-field carrier retries.

Required preflight:

1. `command -v claude`
2. verify `.claude/agents/<agent>.md` exists
3. verify `roles/<agent>.md` exists
4. verify the required output schema exists
5. verify `scripts/extract-claude-result.py` exists

Claude carrier requires network access and working Claude authentication. If the CLI is missing, API/auth is unavailable, network access is blocked, or the non-interactive run cannot obtain required approval, write `carrier-status.json` with `status: carrier_unavailable`, record a concrete reason such as `claude_cli_unavailable`, `claude_api_unreachable`, `claude_auth_unavailable`, or `claude_approval_unavailable`, and use an allowed fallback or stop. Do not guess another Claude invocation.

Codex may run Claude either:

1. inside a trusted project execution with network and non-interactive permissions already configured, or
2. outside the Codex sandbox through a human or higher-level orchestrator that records the same artifact layout.

### Read-only Claude Roles

Read-only Claude roles are `aggressive-designer`, `genius`, and `aufheben-designer`.

The stdout shape, validation-error format, artifact-write contract, and read-only submission ruling are now defined by `.agent-org/tool-io-substrate.md` sections "Stdout Envelope", "Validation Error Shape", "Artifact Vs Stdout Split", and "Read-Only Artifact Submission Ruling".

Recorded gate outcome (controller verification, 2026-06-12, Claude Code CLI current): live scratch run used `claude --print --tools "Bash" --allowedTools "Bash(python3 scripts/submit-result.py *)"` with a prompt asking Claude to run plain `ls`; the off-pattern Bash command succeeded and returned the repository listing. Disposition per the gate: the proposed read-only Claude write path `Bash(python3 scripts/submit-result.py *)` is not adopted; read-only Claude roles keep the extract-then-validate path below, and the write-path question routes to #39. Until the #39 tool-I/O substrate supersedes local v1, `scripts/submit-result.py` remains documented for write-capable carriers such as Codex implementer and for controller-side validation.

Invocation template:

```bash
schema_path="schemas/<schema>.schema.json"
schema_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))))' "$schema_path")"

claude --print \
  --agent "<agent>" \
  --permission-mode plan \
  --tools "Read,Grep,Glob" \
  --allowedTools "Read,Grep,Glob" \
  --json-schema "$schema_json" \
  --output-format json \
  < ".agent-runs/<run_id>/carriers/claude/<agent>/input.md" \
  > ".agent-runs/<run_id>/carriers/claude/<agent>/cli-output.json" \
  2> ".agent-runs/<run_id>/carriers/claude/<agent>/stderr.log"

python3 scripts/extract-claude-result.py \
  --cli-output ".agent-runs/<run_id>/carriers/claude/<agent>/cli-output.json" \
  --out ".agent-runs/<run_id>/carriers/claude/<agent>/result.json"

python3 scripts/validate-bootstrap-pack.py \
  --schema "$schema_path" \
  --instance ".agent-runs/<run_id>/carriers/claude/<agent>/result.json"
```

For `genius`, use `--tools "Read,Grep,Glob,WebSearch,WebFetch"` and `--allowedTools "Read,Grep,Glob,WebSearch,WebFetch"`.

Read-only adapters must not include Bash, Edit, or Write tools.

### Write-capable Claude Roles

Write-capable Claude roles are `security-ci-action-writer` and secondary `implementer`.

Invocation template:

```bash
schema_path="schemas/<schema>.schema.json"
schema_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))))' "$schema_path")"
model_args=()
[ "<adapter-model>" = "inherit" ] || model_args=(--model "<adapter-model>")

claude --print \
  --agent "<agent>" \
  "${model_args[@]}" \
  --permission-mode acceptEdits \
  --tools "Read,Grep,Glob,Bash,Edit,Write" \
  --allowedTools "Read,Grep,Glob,Bash,Edit,Write" \
  --json-schema "$schema_json" \
  --output-format json \
  < ".agent-runs/<run_id>/carriers/claude/<agent>/input.md" \
  > ".agent-runs/<run_id>/carriers/claude/<agent>/cli-output.json" \
  2> ".agent-runs/<run_id>/carriers/claude/<agent>/stderr.log"

python3 scripts/extract-claude-result.py \
  --cli-output ".agent-runs/<run_id>/carriers/claude/<agent>/cli-output.json" \
  --out ".agent-runs/<run_id>/carriers/claude/<agent>/result.json"

python3 scripts/validate-bootstrap-pack.py \
  --schema "$schema_path" \
  --instance ".agent-runs/<run_id>/carriers/claude/<agent>/result.json"
```

Set `<adapter-model>` from the adapter frontmatter. This passes `--model fable` for `security-ci-action-writer` and omits the model flag for adapters with `model: inherit`.

Write-capable Claude roles may write only the scope allowed by their role and input contract.

### Genius Invocation

`genius` requires external research. Its adapter must include web/search/fetch capability when available.

If web/search/fetch tools are unavailable, `genius` must produce a schema-shaped output whose handoff states `external_research_unavailable`. It must not fabricate sources.

For `genius`, `input.md` MUST restate this budget line: `Output budget: JSON object first character, no preamble or code fences; each string <=200 chars with schema hard caps of 400 chars for leaf strings and 600 chars for objective; write handoff_to_aufheben within 800 chars (schema tolerance 890 — the tolerance band absorbs counting error, the 800 target is the instruction; owner-ratified 2026-06-13); kept_hypotheses <=3 by default with schema cap 5; every array <=6 items; total output controller-measured <=32000 bytes; evidence summaries are pointers plus one-line summaries, never essays.` Verified failure mode: unconstrained output reached 22KB and truncated beyond closure repair.

### Aufheben Input Embedding

Before invoking `aufheben-designer`, the controller must compose the aufheben `input.md` so each designer `result.json` is embedded verbatim as raw bytes. The controller must not summarize, reserialize, reorder, or filter the designer JSON inside the aufheben input.

The controller runs the handoff gate before invoking `aufheben-designer`:

```bash
python3 scripts/hash-artifacts.py \
  --verify-embed \
  --composed ".agent-runs/<run_id>/carriers/<carrier>/aufheben-designer/input.md" \
  --source ".agent-runs/<run_id>/carriers/<carrier>/aggressive-designer/result.json" \
  --source ".agent-runs/<run_id>/carriers/<carrier>/conservative-designer/result.json" \
  --source ".agent-runs/<run_id>/carriers/<carrier>/genius/result.json" \
  > ".agent-runs/<run_id>/gates/aufheben-input-embed.json"
```

The gate is raw-byte containment with exactly one trailing-newline difference tolerated per source. A failing report stops the aufheben invocation until the input is recomposed with byte-identical designer results.

### Output Capture

Claude output is valid only after:

1. `cli-output.json` exists
2. `cli-output.json` parses as a Claude CLI result envelope
3. `scripts/extract-claude-result.py` extracts the `result` field into `result.json`
4. `result.json` parses as JSON
5. `result.json` conforms to the role schema
6. `carrier-status.json` records the CLI command, exit status, adapter path, role path, schema path, network/auth status, and fallback status

`--json-schema` is an output constraint, not the validation source of truth. In tool-using runs, `structured_output` may be absent or null. Treat `result` parsing plus schema validation as the main path. `structured_output` is only a fallback when it is present and `result` cannot be parsed.

The invocation templates require Bash because the write-capable template uses an array for optional model arguments.

### Output Repair

Before retrying a carrier response, run `scripts/extract-claude-result.py`. For string `result` values, the extractor first parses intact JSON, then automatically applies bounded closure repair for truncated JSON by appending only JSON closing characters. A successful repaired extraction records `extraction_mode` as `result_closure_repaired`.

If extraction including automatic closure repair, largest-object salvage, and `structured_output` fallback still fails because the carrier returned non-JSON, truncated JSON, or JSON wrapped in explanatory text, or fails role-schema validation:

1. Preserve the failing attempt artifacts.
2. Retry the same carrier once with this extra instruction:

```text
Retry with concise JSON only. Each string must be 400 characters or fewer. Each array must contain 12 items or fewer. Do not include Markdown, code fences, or explanatory text.
```

3. If the retry fails, stop with `carrier_output_invalid`.

`scripts/extract-claude-result.py` may salvage JSON wrapped in prose by parsing from each JSON object start and choosing the largest parseable object. Salvaged output must still pass schema validation.

If the local Claude CLI does not support the invocation template, stop with `claude_invocation_contract_unsupported`.

`.claude/settings.json` sets project default permission mode to `plan` as a safety baseline for human Claude sessions. Role invocation templates override permission mode explicitly.

## Fallback Rule

When a preferred carrier is unavailable:

1. Record `carrier_unavailable`.
2. Use the secondary carrier only if the runtime registry allows it.
3. Preserve the same canonical role spec.
4. Record the fallback in runtime notes.

## Authority Rule

Carrier output is candidate evidence or a structured result. It is not adoption.
