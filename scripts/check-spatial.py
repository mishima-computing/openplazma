#!/usr/bin/env python3
"""Controller-run computable spatial lint for served HTML/CSS surfaces.

Primary input is a site directory served from 127.0.0.1 on an ephemeral port.
The script injects a geometry/style probe into served HTML, captures widths
that Chrome can represent as top-level windows directly, uses a same-origin
iframe harness only for sub-500px widths, extracts a versioned
spatial-facts.v2 blob from dump-dom, and evaluates pure-stdlib checks.

Exit codes, scoped to this script only:
0 all decidable checks pass and no advisory or indeterminate findings exist.
1 at least one decidable check fails.
2 Chrome, launch, probe, server, or facts-version failure prevented a reliable
  live sweep; stderr names the unavailable binary or failing phase and JSON uses
  env-unavailable or schema-error status.
3 decidable checks pass, but tap-target advisory findings or contrast
  indeterminate findings were recorded.

Blob version: spatial-facts.v2. Unknown versions are rejected rather than
guessed. JSON output and per-check finding lists are bounded by FINDING_CAP.

Chrome caveats: Chrome has historically enforced an approximately 500px minimum
top-level window size, so widths below 500px are simulated through same-origin
iframes. Widths at or above 500px are captured as top-level windows to avoid
making dump-dom wait on a harness document that owns network-loading iframes.
Served HTML receives an early CSP meta tag that blocks external fetch, frame,
connect, object, and form targets; this keeps target pages from holding the
harness load open while preserving same-origin CSS, scripts, images, fonts, and
inline styles/scripts needed for local static exports. Headless/headless-shell
packaging split around Chrome 132 can affect binary discovery; set CHROME_BIN or
--chrome when needed. Chrome 149, observed 2026-06-12, can hang when
--user-data-dir is combined with --headless=new and --virtual-time-budget; the
live invocation relies on new headless' ephemeral profile instead.

Known divergence: iframe geometry may differ from a top-level viewport for
vh-dependent layout and position:fixed behavior. A fixture pins the overflow
geometry expected from the Stage-B nav min-content widening class.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from chrome_capture import (  # noqa: E402
    DEFAULT_CHROME_TIMEOUT_SECONDS,
    DEFAULT_WIDTHS,
    FACTS_SCRIPT_ID,
    FACTS_VERSION,
    MIN_TOP_LEVEL_WIDTH,
    PROBE_COMPLETE_ID,
    PROBE_CSP,
    PROBE_SCRIPT_ID,
    VIRTUAL_TIME_BUDGET_MS,
    ChromeUnavailableError,
    chrome_run,
    frame_height,
    inject_probe,
    serve_site,
    site_url,
    with_probe_width,
)

FINDING_CAP = 25
SELECTOR_MAX = 200


class SpatialError(Exception):
    pass


class FactsVersionError(SpatialError):
    pass


class ProbeMissingError(SpatialError):
    pass


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    findings: list[dict[str, Any]]
    finding_count: int = 0
    truncated: bool = False
    deferred: list[dict[str, str]] | None = None

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "status": self.status,
            "findings": self.findings,
            "finding_count": self.finding_count,
            "truncated": self.truncated,
        }
        if self.deferred:
            payload["deferred"] = self.deferred
        return payload


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def clamp_text(value: object, limit: int = SELECTOR_MAX) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def bounded(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    return items[:FINDING_CAP], len(items) > FINDING_CAP


def parse_widths(raw: str) -> list[int]:
    widths: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        width = int(item)
        if width < 240 or width > 4096:
            raise argparse.ArgumentTypeError("widths must be between 240 and 4096 CSS px")
        widths.append(width)
    if not widths:
        raise argparse.ArgumentTypeError("at least one width is required")
    return widths


def parse_css_rgb(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, str):
        return None
    raw = value.strip().lower()
    if raw.startswith("#"):
        hex_value = raw[1:]
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) == 6 and re.fullmatch(r"[0-9a-f]{6}", hex_value):
            return (
                int(hex_value[0:2], 16),
                int(hex_value[2:4], 16),
                int(hex_value[4:6], 16),
                1.0,
            )
    match = re.fullmatch(r"rgba?\(([^)]+)\)", raw)
    if not match:
        return None
    parts = [part.strip() for part in match.group(1).replace("/", ",").split(",")]
    if len(parts) < 3:
        return None
    try:
        rgb = [float(parts[index].rstrip("%")) for index in range(3)]
        alpha = float(parts[3]) if len(parts) >= 4 else 1.0
    except ValueError:
        return None
    if any(part > 100 for part in rgb):
        rgb = [max(0.0, min(255.0, part)) for part in rgb]
    else:
        rgb = [max(0.0, min(255.0, part * 2.55 if "%" in parts[index] else part)) for index, part in enumerate(rgb)]
    return rgb[0], rgb[1], rgb[2], max(0.0, min(1.0, alpha))


def relative_luminance(rgb: tuple[float, float, float, float]) -> float:
    channels = []
    for raw in rgb[:3]:
        c = raw / 255.0
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: tuple[float, float, float, float], background: tuple[float, float, float, float]) -> float:
    lighter = max(relative_luminance(foreground), relative_luminance(background))
    darker = min(relative_luminance(foreground), relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


def is_large_text(element: dict[str, Any]) -> bool:
    try:
        font_size = float(element.get("fontSizePx", 0))
    except (TypeError, ValueError):
        font_size = 0.0
    try:
        font_weight = float(element.get("fontWeight", 400))
    except (TypeError, ValueError):
        font_weight = 400.0
    return font_size >= 24.0 or (font_weight >= 700.0 and font_size >= 18.66)


def validate_facts(facts: dict[str, Any]) -> None:
    version = facts.get("version")
    if version != FACTS_VERSION:
        raise FactsVersionError(f"unsupported spatial facts version: {version!r}; expected {FACTS_VERSION}")
    frames = facts.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ProbeMissingError("spatial facts blob has no frame captures")


def check_overflow(facts: dict[str, Any]) -> CheckResult:
    findings: list[dict[str, Any]] = []
    for frame in facts.get("frames", []):
        viewport = frame.get("viewport", {})
        width = int(frame.get("width", viewport.get("clientWidth", 0)) or 0)
        client_width = float(viewport.get("clientWidth", width) or width)
        scroll_width = float(viewport.get("scrollWidth", client_width) or client_width)
        if scroll_width <= client_width + 1:
            continue
        offenders: list[dict[str, Any]] = []
        for element in frame.get("elements", []):
            rect = element.get("rect", {})
            left = float(rect.get("left", 0) or 0)
            right = float(rect.get("right", 0) or 0)
            elem_width = float(rect.get("width", 0) or 0)
            if right > client_width + 1 or left < -1 or elem_width > client_width + 1:
                offenders.append({
                    "selector": clamp_text(element.get("selector", "")),
                    "rect": {
                        "left": round(left, 2),
                        "right": round(right, 2),
                        "width": round(elem_width, 2),
                    },
                })
        capped, offenders_truncated = bounded(offenders)
        findings.append({
            "width": width,
            "client_width": round(client_width, 2),
            "scroll_width": round(scroll_width, 2),
            "offenders": capped,
            "offender_count": len(offenders),
            "offenders_truncated": offenders_truncated,
        })
    capped_findings, truncated = bounded(findings)
    return CheckResult("overflow", "fail" if findings else "pass", capped_findings, len(findings), truncated)


def check_fixed_bounds(facts: dict[str, Any]) -> CheckResult:
    findings: list[dict[str, Any]] = []
    fail_count = 0
    for frame in facts.get("frames", []):
        viewport = frame.get("viewport", {})
        width = float(viewport.get("clientWidth", frame.get("width", 0)) or 0)
        height = float(viewport.get("clientHeight", frame.get("height", 0)) or 0)
        scroll_width = float(viewport.get("scrollWidth", width) or width)
        grows_document_width = scroll_width > width + 1
        for element in frame.get("elements", []):
            if element.get("position") != "fixed":
                continue
            rect = element.get("rect", {})
            left = float(rect.get("left", 0) or 0)
            top = float(rect.get("top", 0) or 0)
            right = float(rect.get("right", 0) or 0)
            bottom = float(rect.get("bottom", 0) or 0)
            if left < -1 or top < -1 or right > width + 1 or bottom > height + 1:
                clipped_ancestor = element.get("overflowClipAncestor")
                clipped_or_behind = bool(clipped_ancestor) or bool(element.get("zIndexNegative"))
                non_interactive = not element.get("isTarget") and not element.get("isFocusable") and not element.get("isInteractive")
                is_info = non_interactive and clipped_or_behind and not grows_document_width
                finding = {
                    "width": int(frame.get("width", width) or width),
                    "selector": clamp_text(element.get("selector", "")),
                    "class": "decorative-clipped" if is_info else "fail",
                    "status": "info" if is_info else "fail",
                    "viewport": {"width": round(width, 2), "height": round(height, 2)},
                    "rect": {
                        "left": round(left, 2),
                        "top": round(top, 2),
                        "right": round(right, 2),
                        "bottom": round(bottom, 2),
                    },
                    "is_target": bool(element.get("isTarget")),
                    "is_focusable": bool(element.get("isFocusable")),
                    "is_interactive": bool(element.get("isInteractive")),
                    "overflow_clip_ancestor": clipped_ancestor,
                    "z_index": element.get("zIndex"),
                    "document_scroll_width_growth": grows_document_width,
                }
                if not is_info:
                    fail_count += 1
                findings.append(finding)
    capped, truncated = bounded(findings)
    return CheckResult("fixed-element-bounds", "fail" if fail_count else "pass", capped, len(findings), truncated)


def contrast_indeterminate_reason(element: dict[str, Any]) -> str | None:
    bg_kind = str(element.get("backgroundKind", "unresolved"))
    if bg_kind != "solid":
        return f"effective background is {bg_kind}"
    foreground = parse_css_rgb(element.get("color"))
    background = parse_css_rgb(element.get("backgroundColor"))
    if foreground is None:
        return "foreground color is unresolvable"
    if background is None:
        return "effective background color is unresolvable"
    if foreground[3] < 1.0:
        return "foreground color has alpha"
    if background[3] < 1.0:
        return "effective background has alpha"
    return None


def check_contrast(facts: dict[str, Any]) -> CheckResult:
    findings: list[dict[str, Any]] = []
    indeterminate_count = 0
    fail_count = 0
    for frame in facts.get("frames", []):
        width = int(frame.get("width", 0) or 0)
        for element in frame.get("elements", []):
            if element.get("hasText"):
                reason = contrast_indeterminate_reason(element)
                if reason:
                    indeterminate_count += 1
                    findings.append({
                        "status": "indeterminate",
                        "criterion": "SC 1.4.3",
                        "width": width,
                        "selector": clamp_text(element.get("selector", "")),
                        "reason": reason,
                    })
                    continue
                foreground = parse_css_rgb(element.get("color"))
                background = parse_css_rgb(element.get("backgroundColor"))
                assert foreground is not None and background is not None
                ratio = contrast_ratio(foreground, background)
                threshold = 3.0 if is_large_text(element) else 4.5
                status = "pass" if ratio + 1e-9 >= threshold else "fail"
                if status == "fail":
                    fail_count += 1
                    findings.append({
                        "status": status,
                        "criterion": "SC 1.4.3",
                        "width": width,
                        "selector": clamp_text(element.get("selector", "")),
                        "ratio": round(ratio, 3),
                        "threshold": threshold,
                    })
            if element.get("isComponent"):
                bg_reason = contrast_indeterminate_reason(element)
                border = parse_css_rgb(element.get("borderColor"))
                background = parse_css_rgb(element.get("backgroundColor"))
                if bg_reason or border is None or background is None or border[3] < 1.0:
                    indeterminate_count += 1
                    findings.append({
                        "status": "indeterminate",
                        "criterion": "SC 1.4.11",
                        "width": width,
                        "selector": clamp_text(element.get("selector", "")),
                        "reason": bg_reason or "component boundary color is unresolvable or alpha",
                    })
                    continue
                ratio = contrast_ratio(border, background)
                if ratio + 1e-9 < 3.0:
                    fail_count += 1
                    findings.append({
                        "status": "fail",
                        "criterion": "SC 1.4.11",
                        "width": width,
                        "selector": clamp_text(element.get("selector", "")),
                        "ratio": round(ratio, 3),
                        "threshold": 3.0,
                    })
    capped, truncated = bounded(findings)
    status = "fail" if fail_count else ("indeterminate" if indeterminate_count else "pass")
    return CheckResult(
        "contrast",
        status,
        capped,
        len(findings),
        truncated,
        deferred=[{
            "criterion": "SC 1.4.11",
            "scope": "hover/focus/pressed state contrast",
            "reason": "stateful non-text contrast needs state capture and is deferred",
        }],
    )


def check_tap_targets(facts: dict[str, Any]) -> CheckResult:
    findings: list[dict[str, Any]] = []
    for frame in facts.get("frames", []):
        width = int(frame.get("width", 0) or 0)
        for element in frame.get("elements", []):
            if not element.get("isTarget"):
                continue
            rect = element.get("rect", {})
            target_width = float(rect.get("width", 0) or 0)
            target_height = float(rect.get("height", 0) or 0)
            if target_width < 24 or target_height < 24:
                findings.append({
                    "width": width,
                    "selector": clamp_text(element.get("selector", "")),
                    "size": {"width": round(target_width, 2), "height": round(target_height, 2)},
                    "class": "advisory",
                    "criterion": "SC 2.5.8",
                    "note": "24x24 CSS px advisory; spacing, inline, equivalent, essential, and user-agent exceptions are not auto-failed",
                })
    capped, truncated = bounded(findings)
    return CheckResult("tap-target-size", "warn" if findings else "pass", capped, len(findings), truncated)


CHECKS: tuple[Callable[[dict[str, Any]], CheckResult], ...] = (
    check_overflow,
    check_fixed_bounds,
    check_contrast,
    check_tap_targets,
)


def evaluate_facts(facts: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    validate_facts(facts)
    checks: list[CheckResult] = []
    for check in CHECKS:
        try:
            checks.append(check(facts))
        except Exception as exc:  # noqa: BLE001
            checks.append(CheckResult(check.__name__.removeprefix("check_"), "fail", [{
                "error": exc.__class__.__name__,
                "message": clamp_text(exc, 300),
            }], 1, False))

    statuses = [item.status for item in checks]
    if any(status == "fail" for status in statuses):
        code = 1
        status = "fail"
    elif any(status in {"warn", "indeterminate"} for status in statuses):
        code = 3
        status = "advisory-or-indeterminate-only"
    else:
        code = 0
        status = "pass"

    payload = {
        "status": status,
        "exit_code": code,
        "blob_version": facts.get("version"),
        "widths": facts.get("widths", []),
        "finding_cap": FINDING_CAP,
        "checks": [item.to_json() for item in checks],
    }
    return code, payload


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


def extract_facts_from_dom(dom: str) -> dict[str, Any]:
    parser = FactsHTMLParser()
    parser.feed(dom)
    if not parser.marker_found:
        raise ProbeMissingError(f"probe completion marker #{PROBE_COMPLETE_ID} missing from dump-dom output")
    raw = "".join(parser.facts_chunks).strip()
    if not raw:
        raise ProbeMissingError(f"facts script #{FACTS_SCRIPT_ID} missing from dump-dom output")
    try:
        parsed = json.loads(html.unescape(raw))
    except json.JSONDecodeError as exc:
        raise ProbeMissingError(f"facts JSON could not be parsed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ProbeMissingError("facts JSON root is not an object")
    return parsed


def merge_live_facts(widths: list[int], captures: list[dict[str, Any]], modes: list[str]) -> dict[str, Any]:
    frames_by_width: dict[int, dict[str, Any]] = {}
    for capture in captures:
        for frame in capture.get("frames", []):
            frames_by_width[int(frame.get("width", 0) or 0)] = frame
    missing = [width for width in widths if width not in frames_by_width]
    if missing:
        raise ProbeMissingError(f"missing spatial frame capture(s) for width(s): {missing}")
    frames = [frames_by_width[width] for width in widths if width in frames_by_width]
    return {
        "version": FACTS_VERSION,
        "widths": widths,
        "source": {
            "mode": "served-directory-mixed",
            "capture_modes": modes,
            "external_request_policy": "early CSP blocks external fetch/connect/frame/object/form requests in served HTML",
        },
        "frames": frames,
        "notes": [
            f"Widths >= {MIN_TOP_LEVEL_WIDTH}px are captured as top-level Chrome windows.",
            f"Widths < {MIN_TOP_LEVEL_WIDTH}px are captured through same-origin iframes.",
        ],
    }


def run_live(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if args.url:
        try:
            dom = chrome_run(args.url, args.widths, args.chrome, args.virtual_time_budget, args.timeout)
            facts = extract_facts_from_dom(dom)
            return evaluate_facts(facts)
        except ChromeUnavailableError as exc:
            print(str(exc), file=sys.stderr)
            return 2, {"status": "env-unavailable", "exit_code": 2, "error": str(exc)}
        except SpatialError as exc:
            print(f"--url mode is best-effort and could not read injected facts: {exc}", file=sys.stderr)
            return 2, {"status": "env-unavailable", "exit_code": 2, "error": str(exc), "mode": "url-best-effort"}

    root = Path(args.site_dir).resolve()
    if not root.is_dir():
        return 2, {"status": "env-unavailable", "exit_code": 2, "error": f"site directory not found: {root}"}
    server: ThreadingHTTPServer | None = None
    try:
        try:
            small_widths = [width for width in args.widths if width < MIN_TOP_LEVEL_WIDTH]
            direct_widths = [width for width in args.widths if width >= MIN_TOP_LEVEL_WIDTH]
            server, base_url = serve_site(root, small_widths, args.path)
        except OSError as exc:
            raise ChromeUnavailableError(f"local server unavailable on 127.0.0.1: {exc}") from exc
        captures: list[dict[str, Any]] = []
        modes: list[str] = []
        target_url = site_url(base_url, args.path)
        for width in direct_widths:
            dom = chrome_run(
                with_probe_width(target_url, width),
                [width],
                args.chrome,
                args.virtual_time_budget,
                args.timeout,
                window_size=(width, frame_height(width)),
            )
            captures.append(extract_facts_from_dom(dom))
            modes.append(f"top-level:{width}")
        if small_widths:
            harness_url = f"{base_url}/__spatial_harness__.html"
            dom = chrome_run(harness_url, small_widths, args.chrome, args.virtual_time_budget, args.timeout)
            captures.append(extract_facts_from_dom(dom))
            modes.append("same-origin-iframes:<500")
        facts = merge_live_facts(args.widths, captures, modes)
        return evaluate_facts(facts)
    except ChromeUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        return 2, {"status": "env-unavailable", "exit_code": 2, "error": str(exc)}
    except FactsVersionError as exc:
        print(str(exc), file=sys.stderr)
        return 2, {"status": "schema-error", "exit_code": 2, "error": str(exc)}
    except SpatialError as exc:
        print(str(exc), file=sys.stderr)
        return 2, {"status": "env-unavailable", "exit_code": 2, "error": str(exc)}
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()


def load_fixture(name: str) -> dict[str, Any]:
    path = ROOT / "fixtures" / "spatial" / "blobs" / f"{name}.json"
    with path.open(encoding="utf-8") as handle:
        loaded = json.load(handle)
    if not isinstance(loaded, dict):
        raise AssertionError(f"{rel(path)} root is not an object")
    return loaded


def assert_only_chrome_run_invokes_subprocess() -> None:
    import ast

    calls: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self, source_path: Path) -> None:
            self.source_path = source_path
            self.stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_Call(self, node: ast.Call) -> Any:
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if func.value.id == "subprocess":
                    location = rel(self.source_path)
                    function = self.stack[-1] if self.stack else "<module>"
                    calls.append(f"{location}:{function}")
            self.generic_visit(node)

    for source_path in (Path(__file__), ROOT / "scripts/chrome_capture.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        Visitor(source_path).visit(tree)
    expected_calls = [
        "scripts/chrome_capture.py:chrome_version_output",
        "scripts/chrome_capture.py:chrome_run",
    ]
    if calls != expected_calls:
        raise AssertionError(f"subprocess calls must be isolated to Chrome helpers, found {calls}")


def run_self_test() -> tuple[int, dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def record(name: str, func: Callable[[], None]) -> None:
        try:
            func()
            cases.append({"name": name, "passed": True})
        except Exception as exc:  # noqa: BLE001
            cases.append({"name": name, "passed": False, "error": f"{exc.__class__.__name__}: {exc}"})

    def known_bad() -> None:
        code, payload = evaluate_facts(load_fixture("known-bad"))
        if code != 1:
            raise AssertionError(f"expected exit 1, got {code}")
        overflow = next(item for item in payload["checks"] if item["name"] == "overflow")
        at_390 = [item for item in overflow["findings"] if item["width"] == 390]
        if not at_390:
            raise AssertionError("known-bad did not fail overflow at 390")
        offenders = at_390[0]["offenders"]
        if not any("nav.site-nav" in item["selector"] for item in offenders):
            raise AssertionError(f"known-bad missing nav.site-nav offender: {offenders}")
        rect = next(item["rect"] for item in offenders if "nav.site-nav" in item["selector"])
        if rect["right"] != 430 or rect["width"] != 430:
            raise AssertionError(f"iframe fidelity geometry changed: {rect}")

    def known_good() -> None:
        code, payload = evaluate_facts(load_fixture("known-good"))
        if code != 0 or payload["status"] != "pass":
            raise AssertionError(f"expected pass exit 0, got {code}: {payload['status']}")

    def indeterminate_only() -> None:
        code, payload = evaluate_facts(load_fixture("indeterminate-only"))
        if code != 3:
            raise AssertionError(f"expected exit 3, got {code}")
        contrast = next(item for item in payload["checks"] if item["name"] == "contrast")
        statuses = {item["status"] for item in contrast["findings"]}
        if contrast["status"] != "indeterminate" or statuses != {"indeterminate"}:
            raise AssertionError(f"expected only indeterminate contrast, got {contrast}")

    def decorative_clipped_fixed_info() -> None:
        code, payload = evaluate_facts(load_fixture("decorative-clipped-fixed"))
        if code != 0 or payload["status"] != "pass":
            raise AssertionError(f"decorative clipped fixed finding affected exit: {code} {payload['status']}")
        fixed = next(item for item in payload["checks"] if item["name"] == "fixed-element-bounds")
        classes = {item.get("class") for item in fixed["findings"]}
        statuses = {item.get("status") for item in fixed["findings"]}
        if fixed["status"] != "pass" or classes != {"decorative-clipped"} or statuses != {"info"}:
            raise AssertionError(f"expected decorative-clipped info finding, got {fixed}")

    def interactive_unclipped_fixed_fail() -> None:
        code, payload = evaluate_facts(load_fixture("interactive-unclipped-fixed"))
        if code != 1 or payload["status"] != "fail":
            raise AssertionError(f"expected interactive fixed exit 1, got {code}: {payload['status']}")
        fixed = next(item for item in payload["checks"] if item["name"] == "fixed-element-bounds")
        if fixed["status"] != "fail":
            raise AssertionError(f"fixed-element-bounds did not fail: {fixed}")
        if not any(item.get("class") == "fail" and item.get("is_interactive") for item in fixed["findings"]):
            raise AssertionError(f"interactive fixed failure not preserved: {fixed}")

    def unknown_version() -> None:
        try:
            evaluate_facts(load_fixture("unknown-version"))
        except FactsVersionError:
            return
        raise AssertionError("unknown version was not rejected")

    def fixture_html_pair() -> None:
        bad = ROOT / "fixtures/spatial/known-bad/index.html"
        good = ROOT / "fixtures/spatial/known-good/index.html"
        if "min-width: 430px" not in bad.read_text(encoding="utf-8"):
            raise AssertionError("known-bad fixture does not encode min-content widening")
        if not good.is_file():
            raise AssertionError("known-good fixture missing")

    def caps() -> None:
        _code, payload = evaluate_facts(load_fixture("known-bad"))
        for check in payload["checks"]:
            if len(check["findings"]) > FINDING_CAP:
                raise AssertionError(f"{check['name']} exceeded finding cap")
            for finding in check["findings"]:
                offenders = finding.get("offenders", [])
                if len(offenders) > FINDING_CAP:
                    raise AssertionError(f"{check['name']} exceeded offender cap")

    def early_csp_injection() -> None:
        html_doc = b'<!doctype html><html><head><link rel="stylesheet" href="https://cdn.example/x.css"></head><body></body></html>'
        injected = inject_probe(html_doc).decode("utf-8")
        head_end = injected.lower().find("<head>") + len("<head>")
        csp_index = injected.find("Content-Security-Policy")
        probe_index = injected.find(PROBE_SCRIPT_ID)
        link_index = injected.find("<link")
        if not (head_end <= csp_index < probe_index < link_index):
            raise AssertionError("probe CSP/script were not injected before page resources")
        decoded = html.unescape(injected)
        if "connect-src 'none'" not in decoded or "frame-src 'none'" not in decoded:
            raise AssertionError("probe CSP does not block external connect/frame requests")

    record("known_bad_overflow_390_with_selector_and_geometry", known_bad)
    record("known_good_passes_default_widths", known_good)
    record("indeterminate_contrast_exit_3", indeterminate_only)
    record("decorative_clipped_fixed_bounds_info", decorative_clipped_fixed_info)
    record("interactive_unclipped_fixed_bounds_fail", interactive_unclipped_fixed_fail)
    record("unknown_blob_version_rejected", unknown_version)
    record("fixture_html_pair_present", fixture_html_pair)
    record("bounded_json_caps", caps)
    record("early_csp_injection_precedes_resources", early_csp_injection)
    record("subprocess_isolated_to_chrome_run", assert_only_chrome_run_invokes_subprocess)

    failed = [case for case in cases if not case["passed"]]
    return (1 if failed else 0), {
        "status": "fail" if failed else "pass",
        "exit_code": 1 if failed else 0,
        "blob_version": FACTS_VERSION,
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Serve a site directory, capture spatial facts through Chrome, and report computable spatial lint JSON.",
        epilog="Exit 0 pass; 1 decidable fail; 2 Chrome/env/probe unavailable; 3 only advisory tap-target or indeterminate contrast findings.",
    )
    parser.add_argument("site_dir", nargs="?", default=".", help="Site directory to serve from 127.0.0.1.")
    parser.add_argument("--path", default="/", help="Path inside the served site to load in each iframe.")
    parser.add_argument("--url", help="Best-effort URL mode; reliable injection is not guaranteed and is outside acceptance.")
    parser.add_argument("--widths", type=parse_widths, default=list(DEFAULT_WIDTHS), help="Comma-separated CSS widths. Default: 320,390,768,1280.")
    parser.add_argument("--chrome", help="Chrome/Chromium binary path. Defaults to CHROME_BIN or common names.")
    parser.add_argument("--virtual-time-budget", type=int, default=VIRTUAL_TIME_BUDGET_MS, help="Chrome virtual-time budget in ms.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_CHROME_TIMEOUT_SECONDS, help=f"Per-Chrome-run wall-clock timeout in seconds. Default: {DEFAULT_CHROME_TIMEOUT_SECONDS}.")
    parser.add_argument("--facts", help="Evaluate a recorded spatial-facts JSON file without Chrome.")
    parser.add_argument("--self-test", action="store_true", help="Run offline fixtures without Chrome.")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be a positive integer number of seconds")

    if args.self_test:
        code, payload = run_self_test()
    elif args.facts:
        try:
            with Path(args.facts).open(encoding="utf-8") as handle:
                loaded = json.load(handle)
            if not isinstance(loaded, dict):
                raise FactsVersionError("facts root is not an object")
            code, payload = evaluate_facts(loaded)
        except FactsVersionError as exc:
            print(str(exc), file=sys.stderr)
            code, payload = 2, {"status": "schema-error", "exit_code": 2, "error": str(exc)}
    else:
        code, payload = run_live(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
