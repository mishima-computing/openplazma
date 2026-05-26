# Local Technical Appendix

This appendix is for technical participants who want to run the local guided StudyFlow.

## Run The Guided StudyFlow

From the repository root:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

The script creates two local Runs, exports the local Observatory, and exports an Observatory Compare page.

## Inspect RunStore Output

Generated RunStore files are written under:

```text
.openplazma/runs/
```

Each Run includes inspectable JSON and JSONL records such as:

- `run.json`
- `config.json`
- `metrics.jsonl`
- `events.jsonl`
- `manifest.json`
- `artifacts/`

## Inspect Observatory Output

Open:

```text
.openplazma/observatory/index.html
```

The compare page is written under:

```text
.openplazma/observatory/compare/
```

## Cleanup

Remove generated output after the session:

```sh
rm -rf .openplazma
```

## Limitations

- Local-only.
- Generated output is ignored by git.
- No cloud sync.
- No external data.
- No real hardware.
