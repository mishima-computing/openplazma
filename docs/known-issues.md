# Known Issues

## GitHub Pages Deploy Warning

`actions/deploy-pages@v5` currently emits a non-blocking Node `punycode` deprecation warning during the Pages deployment step.

This warning is not the Node.js 20 Actions deprecation warning. The workflows use Node 24-compatible action versions:

- `actions/checkout@v6`
- `actions/setup-node@v6`
- `actions/setup-python@v6`
- `actions/configure-pages@v6`
- `actions/upload-pages-artifact@v5`
- `actions/deploy-pages@v5`

Current status:

- Pages is configured with `build_type: workflow`.
- Current Pages deploy succeeds.
- Public demo returns `200` at `https://mishima-computing.github.io/openplazma/`.
- Revisit when GitHub or the relevant action publishes an update.
- Public demo remains `STATIC_FIXTURE` only.

No other non-blocking release issues are currently documented.
