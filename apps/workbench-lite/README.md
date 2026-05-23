# OpenPlazma Workbench Lite

Workbench Lite is a local JupyterLite site for opening OpenPlazma `STATIC_FIXTURE` notebook examples in a browser. It does not fetch external data, start local JupyterLab, use AI assistance, or connect to hardware.

## Build

```sh
cd apps/workbench-lite
python -m pip install -r requirements.txt
jupyter lite build --lite-dir . --output-dir _output
jupyter lite serve --lite-dir . --output-dir _output
```

Then open the Lab with:

```sh
VITE_OPENPLAZMA_WORKBENCH_LITE_URL=http://127.0.0.1:8000/lab/index.html?path=openplazma/experiment_notebook.ipynb
```

The Lab passes ExperimentContext through browser `localStorage` and an `opContext` URL query parameter. Build output in `_output/` is generated and must not be committed.
