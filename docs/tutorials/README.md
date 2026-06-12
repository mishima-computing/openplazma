# Tutorials

OpenPlazma tutorials are guided missions for learning read-only plasma signal analysis, evidence logging, and comparison workflows.

Available tutorials:

- [Read the Signal](read-the-signal/README.md)
- [Investigate Will-o'-the-wisp](investigate-will-o-wisp.md)

Workshop materials:

- [Teacher / Workshop Pack](../../teacher-kit/README.md)

Public demo:

```text
https://mishima-computing.github.io/openplazma/
```

## Paths

Browser-only path:

- Requires only a browser.
- Opens the public Lab.
- Uses `STATIC_FIXTURE` data only.
- Does not write to a local RunStore.

Local technical path:

- Requires Git, Node/Corepack, and Python.
- Runs the Read the Signal guided StudyFlow locally.
- Creates local Runs under `.openplazma/`.
- Exports local Observatory and Compare pages.
- Creates local investigation reports under `.openplazma/investigation-reports/`.

## Mission Boundary

These tutorials use `STATIC_FIXTURE` data only in the public path.

No public data ingestion, grading or scoring, AI assist, cloud sync, hosted Observatory, command/control path, hazardous procedure, or standalone safety-critical design decision is included.

The mission is not to avoid real engineering judgment. The mission is to practice the read-only evidence path that real engineering judgment needs: signal provenance, observation, hypothesis, metrics, run history, and comparison.
