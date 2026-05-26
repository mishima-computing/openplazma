# One-minute Demo Path

Use this path when showing OpenPlazma quickly.

## Before The Demo

If showing the local Observatory or Compare page, generate local output first:

```sh
python scripts/run-guided-study-flow.py --run-store .openplazma --clean
```

## Demo Path

1. Open the public demo:

   ```text
   https://mishima-computing.github.io/openplazma/
   ```

2. Show the `STATIC_FIXTURE` Signal in the Lab.
3. Point to the observation and hypothesis workflow.
4. Open the Read the Signal Tutorial:

   ```text
   docs/tutorials/read-the-signal/README.md
   ```

5. If local output is already generated, show:

   ```text
   .openplazma/observatory/index.html
   .openplazma/observatory/compare/...
   ```

6. Close with the boundary:

   This demo uses `STATIC_FIXTURE` data only. It does not control hardware. It is not a validated fusion simulator, reactor design tool, or real hardware control system.

## What To Avoid

- Do not claim public data ingestion exists.
- Do not claim AI assist exists.
- Do not claim grading or scoring exists.
- Do not claim hosted Observatory exists.
- Do not imply real hardware operation.
