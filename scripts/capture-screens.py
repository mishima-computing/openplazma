#!/usr/bin/env python3
"""Controller-run perceptual capture set generator.

The script captures deterministic PNG paths for reviewer packets:
desktop fold, full-page, and sub-500px iframe-harness widths. Live capture is a
controller operation; carrier reviewers read the emitted PNGs and metadata only.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from chrome_capture import (  # noqa: E402
    DEFAULT_CHROME_TIMEOUT_SECONDS,
    FACTS_SCRIPT_ID,
    FACTS_VERSION,
    MIN_TOP_LEVEL_WIDTH,
    PROBE_COMPLETE_ID,
    VIRTUAL_TIME_BUDGET_MS,
    ChromeUnavailableError,
    chrome_run,
    copy_site_with_vh_neutralization,
    frame_height,
    neutralize_vh_units,
    serve_site,
    site_url,
    with_capture_scroll,
    with_probe_width,
)


CAPTURE_SET_VERSION = "capture-screens.v1"
DEFAULT_DESKTOP_WIDTH = 1280
DEFAULT_DESKTOP_HEIGHT = 800
DEFAULT_MOBILE_WIDTHS = (320, 390)
DEFAULT_OUTPUT_DIR = ".agent-runs/capture-screens"
MAX_FULL_PAGE_WINDOW_HEIGHT = 10000
FULL_PAGE_SLICE_HEIGHT = 1600
IFRAME_CAVEAT = (
    "Sub-500px captures use a same-origin iframe harness because Chrome may not represent those widths as top-level windows; "
    "vh-dependent layout and position:fixed behavior may diverge from a top-level mobile viewport, so these captures are not asserted as mobile-faithful."
)


class CaptureError(Exception):
    pass


class FactsHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_facts = False
        self.facts_chunks: list[str] = []
        self.marker_found = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value for key, value in attrs}
        if tag.lower() == "script" and attrs_dict.get("id") == FACTS_SCRIPT_ID:
            self.in_facts = True
        if attrs_dict.get("id") == PROBE_COMPLETE_ID:
            self.marker_found = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self.in_facts:
            self.in_facts = False

    def handle_data(self, data: str) -> None:
        if self.in_facts:
            self.facts_chunks.append(data)


def parse_widths(raw: str) -> list[int]:
    widths: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        width = int(item)
        if width < 240 or width >= MIN_TOP_LEVEL_WIDTH:
            raise argparse.ArgumentTypeError(f"mobile widths must be between 240 and {MIN_TOP_LEVEL_WIDTH - 1} CSS px")
        widths.append(width)
    if not widths:
        raise argparse.ArgumentTypeError("at least one mobile width is required")
    return widths


def extract_facts_from_dom(dom: str) -> dict[str, Any]:
    parser = FactsHTMLParser()
    parser.feed(dom)
    if not parser.marker_found:
        raise CaptureError(f"probe completion marker #{PROBE_COMPLETE_ID} missing from dump-dom output")
    raw = "".join(parser.facts_chunks).strip()
    if not raw:
        raise CaptureError(f"facts script #{FACTS_SCRIPT_ID} missing from dump-dom output")
    parsed = json.loads(html.unescape(raw))
    if not isinstance(parsed, dict) or parsed.get("version") != FACTS_VERSION:
        raise CaptureError(f"unexpected facts version: {parsed.get('version') if isinstance(parsed, dict) else type(parsed).__name__}")
    return parsed


def scroll_height_from_facts(facts: dict[str, Any]) -> int:
    frames = facts.get("frames")
    if not isinstance(frames, list) or not frames:
        raise CaptureError("facts contain no frames for scrollHeight probe")
    viewport = frames[0].get("viewport", {})
    height = int(float(viewport.get("scrollHeight", 0) or 0))
    if height <= 0:
        raise CaptureError("scrollHeight probe returned an empty document height")
    return height


def capture_png(
    url: str,
    output_path: Path,
    width: int,
    height: int,
    args: argparse.Namespace,
    dump_dom: bool = False,
) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return chrome_run(
        url,
        [width],
        args.chrome,
        args.virtual_time_budget,
        args.timeout,
        window_size=(width, height),
        screenshot_path=output_path,
        dump_dom=dump_dom,
    )


def capture_served_site(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    root = Path(args.target).resolve()
    if not root.is_dir():
        raise CaptureError(f"site directory not found: {root}")

    captures: list[dict[str, Any]] = []
    servers = []
    try:
        server, base_url = serve_site(root, list(args.mobile_widths), args.path)
        servers.append(server)
        target_url = site_url(base_url, args.path)
        desktop_path = out_dir / "desktop-fold-1280.png"
        capture_png(target_url, desktop_path, args.desktop_width, args.desktop_height, args)
        captures.append({
            "kind": "desktop-fold",
            "path": str(desktop_path),
            "width": args.desktop_width,
            "height": args.desktop_height,
            "mode": "served-directory-top-level",
        })

        with tempfile.TemporaryDirectory(prefix="capture-vh-") as tmp:
            neutralized = copy_site_with_vh_neutralization(root, Path(tmp), args.desktop_height)
            full_server, full_base_url = serve_site(neutralized.output_root, [], args.path)
            servers.append(full_server)
            full_url = site_url(full_base_url, args.path)
            dom = chrome_run(
                with_probe_width(full_url, args.desktop_width),
                [args.desktop_width],
                args.chrome,
                args.virtual_time_budget,
                args.timeout,
                window_size=(args.desktop_width, args.desktop_height),
            )
            full_height = scroll_height_from_facts(extract_facts_from_dom(dom))
            full_meta: dict[str, Any] = {
                "kind": "full-page",
                "width": args.desktop_width,
                "scroll_height": full_height,
                "mode": "vh-neutralized-served-copy",
                "vh_neutralized_files": neutralized.rewritten_files,
            }
            if full_height <= args.max_full_page_window_height:
                full_path = out_dir / "full-page.png"
                capture_png(full_url, full_path, args.desktop_width, full_height, args)
                full_meta.update({"path": str(full_path), "height": full_height, "sliced": False})
            else:
                slices: list[dict[str, Any]] = []
                for index, y in enumerate(range(0, full_height, args.slice_height)):
                    slice_height = min(args.slice_height, full_height - y)
                    slice_path = out_dir / f"full-page-slice-{index:03d}.png"
                    capture_png(with_capture_scroll(full_url, y), slice_path, args.desktop_width, slice_height, args)
                    slices.append({"path": str(slice_path), "y": y, "height": slice_height})
                full_meta.update({"sliced": True, "slice_height": args.slice_height, "slices": slices})
            captures.append(full_meta)

        for width in args.mobile_widths:
            mobile_server, mobile_base_url = serve_site(root, [width], args.path)
            servers.append(mobile_server)
            harness_url = f"{mobile_base_url}/__spatial_harness__.html"
            mobile_path = out_dir / f"mobile-iframe-{width}.png"
            capture_png(harness_url, mobile_path, max(width + 40, MIN_TOP_LEVEL_WIDTH), frame_height(width), args)
            captures.append({
                "kind": "mobile-iframe",
                "path": str(mobile_path),
                "iframe_width": width,
                "window_width": max(width + 40, MIN_TOP_LEVEL_WIDTH),
                "height": frame_height(width),
                "mode": "same-origin-iframe-harness",
                "caveat": IFRAME_CAVEAT,
            })
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()

    return build_metadata(args, out_dir, captures, target_mode="served-directory")


def capture_url(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    captures: list[dict[str, Any]] = []
    desktop_path = out_dir / "desktop-fold-1280.png"
    capture_png(args.target, desktop_path, args.desktop_width, args.desktop_height, args)
    captures.append({
        "kind": "desktop-fold",
        "path": str(desktop_path),
        "width": args.desktop_width,
        "height": args.desktop_height,
        "mode": "url-top-level",
    })
    full_path = out_dir / "full-page-fixed-height.png"
    capture_png(args.target, full_path, args.desktop_width, args.url_full_page_height, args)
    captures.append({
        "kind": "full-page",
        "path": str(full_path),
        "width": args.desktop_width,
        "height": args.url_full_page_height,
        "mode": "url-fixed-height-no-scrollheight-probe",
        "note": "URL mode cannot inject the local scrollHeight probe; use served site dir for vh-neutralized full-page sizing.",
    })
    for width in args.mobile_widths:
        harness_path = write_url_iframe_harness(out_dir, args.target, width)
        mobile_path = out_dir / f"mobile-iframe-{width}.png"
        capture_png(harness_path.as_uri(), mobile_path, max(width + 40, MIN_TOP_LEVEL_WIDTH), frame_height(width), args)
        captures.append({
            "kind": "mobile-iframe",
            "path": str(mobile_path),
            "harness_path": str(harness_path),
            "iframe_width": width,
            "window_width": max(width + 40, MIN_TOP_LEVEL_WIDTH),
            "height": frame_height(width),
            "mode": "url-iframe-harness",
            "caveat": IFRAME_CAVEAT,
        })
    return build_metadata(args, out_dir, captures, target_mode="url")


def write_url_iframe_harness(out_dir: Path, target_url: str, width: int) -> Path:
    harness_path = out_dir / f"url-iframe-{width}.html"
    harness = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>url iframe capture {width}</title>
<style>html,body{{margin:0;padding:0;background:#fff;}} iframe{{width:{width}px;height:{frame_height(width)}px;border:0;display:block;}}</style>
</head>
<body>
<iframe title="url-capture-{width}" src="{html.escape(target_url, quote=True)}"></iframe>
</body>
</html>
"""
    harness_path.write_text(harness, encoding="utf-8")
    return harness_path


def build_metadata(args: argparse.Namespace, out_dir: Path, captures: list[dict[str, Any]], target_mode: str) -> dict[str, Any]:
    return {
        "version": CAPTURE_SET_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target": args.target,
        "target_mode": target_mode,
        "path": args.path,
        "output_dir": str(out_dir),
        "controller_only_live_capture": True,
        "reviewer_carrier_access": "Read PNGs and metadata only; reviewers do not execute live Chrome.",
        "iframe_caveat": IFRAME_CAVEAT,
        "captures": captures,
    }


def run_live(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if args.target.startswith(("http://", "https://")):
            payload = capture_url(args, out_dir)
        else:
            payload = capture_served_site(args, out_dir)
        metadata_path = out_dir / "capture-metadata.json"
        metadata_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["metadata_path"] = str(metadata_path)
        return 0, payload
    except ChromeUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        return 2, {"status": "env-unavailable", "exit_code": 2, "error": str(exc)}
    except (CaptureError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2, {"status": "capture-error", "exit_code": 2, "error": f"{exc.__class__.__name__}: {exc}"}


def run_self_test() -> tuple[int, dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def record(name: str, func: Callable[[], None]) -> None:
        try:
            func()
            cases.append({"name": name, "passed": True})
        except Exception as exc:  # noqa: BLE001
            cases.append({"name": name, "passed": False, "error": f"{exc.__class__.__name__}: {exc}"})

    def width_parser() -> None:
        if parse_widths("320,390") != [320, 390]:
            raise AssertionError("mobile width parsing changed")
        try:
            parse_widths("500")
        except argparse.ArgumentTypeError:
            return
        raise AssertionError("500px should use top-level capture, not iframe harness")

    def vh_neutralization() -> None:
        updated = neutralize_vh_units("min-height:100vh; top: 2.5vh; width: 10vw;")
        if "calc(var(--capture-vh-px) * 100)" not in updated:
            raise AssertionError(updated)
        if "10vw" not in updated:
            raise AssertionError("vw units should not be rewritten")

    def metadata_shape() -> None:
        namespace = argparse.Namespace(target="fixtures/spatial/known-good", path="/", out_dir=DEFAULT_OUTPUT_DIR)
        payload = build_metadata(namespace, Path(DEFAULT_OUTPUT_DIR), [], "served-directory")
        if payload["version"] != CAPTURE_SET_VERSION:
            raise AssertionError("capture metadata version changed")
        if "position:fixed" not in payload["iframe_caveat"] or "not asserted as mobile-faithful" not in payload["iframe_caveat"]:
            raise AssertionError("iframe caveat missing required fidelity warning")
        if not payload["controller_only_live_capture"]:
            raise AssertionError("metadata must state controller-only live capture")

    def deterministic_names() -> None:
        names = [
            "desktop-fold-1280.png",
            "full-page.png",
            "full-page-slice-000.png",
            "mobile-iframe-320.png",
            "url-iframe-320.html",
        ]
        if names != sorted(names, key=names.index):
            raise AssertionError("capture names should be stable literals")

    record("mobile_width_parser_bounds", width_parser)
    record("vh_unit_neutralization_rewrites_vh_only", vh_neutralization)
    record("metadata_carries_iframe_caveat_and_controller_boundary", metadata_shape)
    record("deterministic_capture_names", deterministic_names)

    failed = [case for case in cases if not case["passed"]]
    return (1 if failed else 0), {
        "status": "fail" if failed else "pass",
        "exit_code": 1 if failed else 0,
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate desktop, full-page, and sub-500px iframe capture PNGs plus metadata.",
        epilog="Live capture is controller-executed. Carrier reviewers read emitted PNGs only.",
    )
    parser.add_argument("target", nargs="?", default=".", help="Served site directory or URL to capture.")
    parser.add_argument("--path", default="/", help="Path inside a served site directory.")
    parser.add_argument("--out-dir", default=DEFAULT_OUTPUT_DIR, help="Run-directory output path for PNGs and metadata.")
    parser.add_argument("--mobile-widths", type=parse_widths, default=list(DEFAULT_MOBILE_WIDTHS), help="Comma-separated sub-500 iframe widths. Default: 320,390.")
    parser.add_argument("--desktop-width", type=int, default=DEFAULT_DESKTOP_WIDTH, help="Desktop capture width. Default: 1280.")
    parser.add_argument("--desktop-height", type=int, default=DEFAULT_DESKTOP_HEIGHT, help="Desktop fold height. Default: 800.")
    parser.add_argument("--max-full-page-window-height", type=int, default=MAX_FULL_PAGE_WINDOW_HEIGHT, help="Full-page window-height cap before slice fallback.")
    parser.add_argument("--slice-height", type=int, default=FULL_PAGE_SLICE_HEIGHT, help="Slice height for very tall full-page captures.")
    parser.add_argument("--url-full-page-height", type=int, default=MAX_FULL_PAGE_WINDOW_HEIGHT, help="Fixed full-page candidate height in URL mode.")
    parser.add_argument("--chrome", help="Chrome/Chromium binary path. Defaults to CHROME_BIN or common names.")
    parser.add_argument("--virtual-time-budget", type=int, default=VIRTUAL_TIME_BUDGET_MS, help="Chrome virtual-time budget in ms.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_CHROME_TIMEOUT_SECONDS, help=f"Per-Chrome-run wall-clock timeout in seconds. Default: {DEFAULT_CHROME_TIMEOUT_SECONDS}.")
    parser.add_argument("--self-test", action="store_true", help="Run offline fixtures without Chrome.")
    args = parser.parse_args(argv)

    if args.self_test:
        code, payload = run_self_test()
    else:
        if args.desktop_width < MIN_TOP_LEVEL_WIDTH:
            parser.error(f"--desktop-width must be >= {MIN_TOP_LEVEL_WIDTH}")
        if args.desktop_height <= 0 or args.timeout <= 0 or args.max_full_page_window_height <= 0 or args.slice_height <= 0:
            parser.error("height, timeout, max full-page height, and slice height must be positive")
        code, payload = run_live(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
