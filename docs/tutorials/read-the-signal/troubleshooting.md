# Troubleshooting

## Public Demo Does Not Load

- Refresh the page.
- Confirm the URL is `https://mishima-computing.github.io/openplazma/`.
- Try another browser if available.
- Do not change browser security settings broadly.

## Workbench Does Not Open

- Return to the Lab and use `Open Experiment Notebook` again.
- Confirm the Workbench URL starts with `/openplazma/workbench/lab/index.html`.
- Continue the browser tour without Workbench if needed.

## Python Command Not Found

- Try the Python launcher available in your environment.
- On Windows, `py` may be available.
- Confirm Python is installed before running the local mission.

## pnpm Command Not Found

Use Corepack:

```sh
corepack pnpm install --frozen-lockfile
```

## Dependencies Not Installed

Run:

```sh
corepack pnpm install --frozen-lockfile
cd python/openplazma
python -m pip install -e ".[dev]"
cd ../..
```

## .openplazma Output Not Visible

Run the local mission:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

Then inspect:

```text
.openplazma/
```

## Generated Output Accidentally Created

Clean generated output:

```sh
rm -rf .openplazma
```

## Validation Fails

- Read the first failing command output.
- Re-run only after fixing the reported issue.
- Do not add credentials, secrets, or private data to fix validation.

## Browser Cannot Open Local HTML

Some environments restrict local files. If `.openplazma/observatory/index.html` does not open directly, use a local static file viewer already approved in your environment. Do not disable broad browser security settings.
