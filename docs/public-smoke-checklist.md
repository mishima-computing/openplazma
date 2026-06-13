# Public Smoke Checklist

Use this checklist after deployments to the public static demo.

Demo URL:

```text
https://mishima-computing.github.io/openplazma/
```

## Scope

- The demo uses `STATIC_FIXTURE` data only.
- The demo presents OpenPlazma as read-only signal analysis and decision support.
- The demo does not fetch external fusion data.
- The demo does not provide AI assist.
- The demo does not provide command/control actions.
- The demo must not include hazardous operating procedures.
- The demo must not present itself as the sole authority for safety-critical operation or reactor design decisions.

## Browser Smoke

- Open `https://mishima-computing.github.io/openplazma/`.
- Confirm the Lab loads without a blocking browser console error.
- Confirm the sample shot is visible.
- Confirm the selected signal chart renders.
- Enter a short observation in the Observation Notebook.
- Add or edit a hypothesis if available.
- Export a StudyRecord JSON.
- Export an ExperimentContext JSON.
- Click `Open Experiment Notebook`.
- Confirm the Workbench opens under `/openplazma/workbench/lab/index.html`.
- Confirm the opened Workbench URL includes an `opContext` query parameter.
- Confirm the notebook path is `openplazma/experiment_notebook.ipynb`.
- Confirm no real hardware instructions appear.
- Confirm no command/control action appears.
- Confirm no claim appears that OpenPlazma alone validates a physical process.
- Confirm no claim appears that OpenPlazma alone makes reactor-design decisions.
- Confirm no reactor-control or facility-control action appears.
- Confirm no external data is fetched.
- Confirm the public demo preserves provenance, assumptions, and limitations.
- If checking tutorials, confirm [Read the Signal](tutorials/read-the-signal/README.md) still points to the current public demo and `STATIC_FIXTURE` scope.

## Static Asset Smoke

Confirm these URLs return `200`:

- `https://mishima-computing.github.io/openplazma/`
- `https://mishima-computing.github.io/openplazma/workbench/lab/index.html`
- `https://mishima-computing.github.io/openplazma/workbench/files/openplazma/experiment_notebook.ipynb`
- `https://mishima-computing.github.io/openplazma/workbench/files/openplazma/sample-experiment-context.json`
- `https://mishima-computing.github.io/openplazma/workbench/files/openplazma/signals/plasma_current.json`

Repository documentation smoke:

- `docs/tutorials/README.md`
- `docs/tutorials/read-the-signal/README.md`
- `docs/tutorials/read-the-signal/00-mission-briefing.md`
- `docs/real-data-fixtures.md`
- `docs/observatory-mvp.md`

Local frozen public-observation smoke, outside the hosted demo:

- Run `python3 scripts/run-public-observation-lineage-audit.py --run-store /tmp/openplazma-lineage-runstore --output-dir /tmp/openplazma-lineage-observatory --clean`.
- Confirm exactly two RunStore runs are created in one run group: `early-even` and `late-mixed`.
- Confirm each run has one `observation_lineage_audit` artifact and `fusionStatus` remains `unsupported`.
- Confirm `/tmp/openplazma-lineage-observatory/index.html` shows `Lineage Audit`, `early-even`, `late-mixed`, and no script/form/button/external URL controls.

## Notebook Smoke

- Confirm the notebook text states `STATIC_FIXTURE` only.
- Confirm the notebook states it is read-only analysis and decision support.
- Confirm the notebook states it does not control equipment or provide hazardous procedures.
- Run the notebook cells if the browser environment is responsive.
- Confirm the signal plot appears from the static signal JSON.

## Reporting

Expected result: every check above passes without expanding the public demo beyond `STATIC_FIXTURE` data and read-only decision-support workflows.

If a check fails, capture the browser, operating system, public URL, relevant console error, and the step that failed.

File feedback using the GitHub issue templates:

- Bug report for reproducible failures.
- Demo feedback for usability or clarity.
- Scientific scope or safety concern for provenance, claim strength, or safety-boundary issues.
