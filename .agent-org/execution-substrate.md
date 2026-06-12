# Execution Substrate

This repository defines a small AI Quality Bootstrap substrate for a final eight-agent roster.

## Active Agents

```text
functional-ci-action-writer
security-ci-action-writer
nonfunctional-ci-action-writer
aggressive-designer
conservative-designer
genius
aufheben-designer
implementer
```

## Separation

```yaml
agents:
  - functional-ci-action-writer
  - security-ci-action-writer
  - nonfunctional-ci-action-writer
  - aggressive-designer
  - conservative-designer
  - genius
  - aufheben-designer
  - implementer
protocol:
  - codex-main-controller
subsystems:
  - local-tooling
  - gate-reporting
  - artifact-hashing
```

Codex main may coordinate execution, but it is protocol, not an agent.

Deterministic tooling may collect evidence and hash artifacts, but it is subsystem behavior, not an agent.

## Carrier Directories

```text
.codex/
.codex/agents/
.claude/
.claude/agents/
.antigravity/
```

Antigravity is reserved. It has no active agents in the current roster.

## Runtime Artifacts

Runtime artifacts belong under:

```text
.agent-runs/<run_id>/
```

`.agent-runs/` is ignored by git.

Raw prompts, stdout, stderr, screenshots, recordings, scratchpads, and unreviewed outputs must not be committed.

## Authority

Agents do not claim adoption. Human review or repository process decides whether outputs are accepted.
