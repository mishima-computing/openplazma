# Setup Checklist

## A. Browser-only Path

- Open the public demo:

```text
https://mishima-computing.github.io/openplazma/
```

- Confirm the Lab loads.
- Confirm the `STATIC_FIXTURE` scope is visible.
- Confirm the Workbench opens if needed.
- Confirm the participant handout is available.

## B. Local Technical Path

Clone the repository:

```sh
git clone https://github.com/mishima-computing/openplazma.git
cd openplazma
```

Install and check the TypeScript workspace:

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm typecheck
corepack pnpm test
```

Install and check the Python SDK:

```sh
cd python/openplazma
python -m pip install -e ".[dev]"
python -m pytest
cd ../..
```

Run repository hygiene:

```sh
python scripts/check-public-repo-hygiene.py
```

Run the guided Mission:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

Confirm:

- `.openplazma/observatory/index.html` exists.
- `.openplazma/observatory/compare/...` exists.
- `.openplazma/` is not committed.

Clean generated output after the session:

```sh
rm -rf .openplazma
```

## Notes

- If `pnpm` is unavailable, use `corepack pnpm`.
- The Python command may vary by system.
- No external data or cloud service is required.
- Do not add credentials, secrets, private data, or restricted data.
