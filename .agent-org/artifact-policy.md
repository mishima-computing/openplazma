# Artifact Policy

## Runtime Artifacts

Runtime artifacts are stored under:

```text
.agent-runs/<run_id>/
```

This directory is ignored by git.

## Standard Run Layout

```text
.agent-runs/
  <run_id>/
    intake/
    carriers/
    results/
    gates/
    worktrees/
    logs/
```

## Do Not Commit

Do not commit:

- raw prompts
- raw stdout
- raw stderr
- raw model transcripts
- screenshots
- recordings
- unreviewed outputs
- local worktrees
- raw tool logs
- secrets
- credentials
- production data
- customer data

## May Commit

The following may be committed only when intentionally reviewed:

- role specs
- carrier adapters
- schemas
- deterministic scripts
- bootstrap policies
- accepted documentation

## Hashing

When practical, record SHA-256 hashes for structured outputs and patches.

## History

Human-readable summaries may later be stored under:

```text
.agent-org/history/
```
