from __future__ import annotations

import runpy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_pages_build_script_constants() -> None:
    script = runpy.run_path(REPO_ROOT / "scripts" / "build-pages-site.py")

    assert script["PAGES_DIR"] == REPO_ROOT / "dist" / "pages"
    assert script["PAGES_WORKBENCH_DIR"] == REPO_ROOT / "dist" / "pages" / "workbench"
    assert script["LAB_BASE_PATH"] == "./"
    assert (
        script["PAGES_WORKBENCH_LITE_URL"]
        == "/openplazma/workbench/lab/index.html?path=openplazma/experiment_notebook.ipynb"
    )


def test_hygiene_rejects_pages_build_outputs() -> None:
    script = runpy.run_path(REPO_ROOT / "scripts" / "check-public-repo-hygiene.py")

    assert script["path_reasons"]("dist/pages/index.html")
    assert script["path_reasons"]("dist/pages/workbench/lab/index.html")
    assert script["path_reasons"]("apps/workbench-lite/_output/lab/index.html")
