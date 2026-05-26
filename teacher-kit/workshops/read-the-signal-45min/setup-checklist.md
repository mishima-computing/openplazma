# Setup Checklist

## A. Browser-Only Path

- Open `https://mishima-computing.github.io/openplazma/`.
- Confirm the Lab loads.
- Confirm the selected signal appears.
- Confirm the page states or links to `STATIC_FIXTURE`-only scope.
- Click `Open Experiment Notebook`.
- Confirm Workbench opens.
- Keep the participant handout available.

This path does not require cloud services, accounts, external data, or real hardware.

## B. Local Technical Path

From a local repository clone:

```sh
corepack pnpm typecheck
corepack pnpm test
cd python/openplazma
python -m pytest
cd ../..
```

Run the guided StudyFlow:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

Open the local Observatory output:

```text
.openplazma/observatory/index.html
```

Clean generated output after the session:

```sh
rm -rf .openplazma
```

This path writes only local generated files under `.openplazma/`.
