# Bootstrap Entrypoint

`bootstrap/codex-bootstrap.md` is the canonical copy-paste Codex entrypoint.

Target repositories should not regenerate role specs, schemas, policies, or carrier adapters. This repository is the source pack for AI Quality Bootstrap.

Canonical roles live under `roles/`.

Carrier adapters live under:

- `.codex/agents/`
- `.claude/agents/`

Runtime artifacts created by target runs belong under `.agent-runs/` and must remain ignored.

Previous repository content and draft role material are preserved under `Legacy/`.
