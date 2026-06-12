#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any

CLOSURE_REPAIR_SUFFIX_CHARS = '"}]'
CLOSURE_REPAIR_MAX_SUFFIX_LENGTH = 6


def fail(message: str) -> int:
    print(json.dumps({"status": "fail", "error": message}, ensure_ascii=False), file=sys.stderr)
    return 1


def parse_json_object(value: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(value)
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)
    if not isinstance(parsed, dict):
        return None, "parsed_result_must_be_object"
    return parsed, None


def repair_truncated_json(value: str) -> tuple[dict[str, Any] | None, str | None]:
    # 3^1 + ... + 3^6 = 1092 bounded parse attempts.
    last_error: str | None = None
    for length in range(1, CLOSURE_REPAIR_MAX_SUFFIX_LENGTH + 1):
        for suffix_chars in itertools.product(CLOSURE_REPAIR_SUFFIX_CHARS, repeat=length):
            parsed, error = parse_json_object(value + "".join(suffix_chars))
            if parsed is not None:
                return parsed, None
            last_error = error
    return None, last_error or "closure_repair_failed"


def salvage_json_object(value: str) -> tuple[dict[str, Any] | None, str | None]:
    decoder = json.JSONDecoder()
    largest: dict[str, Any] | None = None
    largest_size = -1
    for index, char in enumerate(value):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            size = len(json.dumps(parsed, ensure_ascii=False))
            if size > largest_size:
                largest = parsed
                largest_size = size
    if largest is not None:
        return largest, None
    return None, "no_json_object_found"


def extract_result_string(value: str) -> tuple[dict[str, Any] | None, str, str | None]:
    extracted, parse_error = parse_json_object(value)
    if extracted is not None:
        return extracted, "result", None

    extracted, repair_error = repair_truncated_json(value)
    if extracted is not None:
        return extracted, "result_closure_repaired", None

    extracted, salvage_error = salvage_json_object(value)
    if extracted is not None:
        return extracted, "result_salvaged", None

    return (
        None,
        "result",
        f"result_field_is_not_json: {parse_error}; repair_error: {repair_error}; salvage_error: {salvage_error}",
    )


def extract_envelope(envelope: object) -> tuple[dict[str, Any] | None, str, str | None]:
    if not isinstance(envelope, dict):
        return None, "result", "cli_output_must_be_object"

    if envelope.get("type") != "result":
        return None, "result", "cli_output_type_must_be_result"

    if envelope.get("is_error") is True:
        return None, "result", f"carrier_error: {envelope.get('result', 'unknown_error')}"

    if "result" not in envelope:
        return None, "result", "cli_output_missing_result"

    result = envelope["result"]
    if isinstance(result, str):
        extracted, extraction_mode, error = extract_result_string(result)
        if extracted is not None:
            return extracted, extraction_mode, None

        structured_output = envelope.get("structured_output")
        if isinstance(structured_output, dict):
            return structured_output, "structured_output_fallback", None
        return None, extraction_mode, error

    if isinstance(result, dict):
        return result, "result", None

    structured_output = envelope.get("structured_output")
    if isinstance(structured_output, dict):
        return structured_output, "structured_output_fallback", None
    return None, "result", "result_field_must_be_json_object_or_json_string"


def extract_raw_text(value: str) -> tuple[dict[str, Any] | None, str, str | None]:
    return extract_result_string(value)


def _assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _self_test_missing_single_closing_brace() -> None:
    extracted, extraction_mode, error = extract_envelope({
        "type": "result",
        "is_error": False,
        "result": '{"outer":{"inner":1}',
    })
    _assert_equal(error, None, "missing single closing brace error")
    _assert_equal(extraction_mode, "result_closure_repaired", "missing single closing brace mode")
    _assert_equal(extracted, {"outer": {"inner": 1}}, "missing single closing brace extraction")


def _self_test_missing_closing_quote_plus_brace() -> None:
    extracted, extraction_mode, error = extract_envelope({
        "type": "result",
        "is_error": False,
        "result": '{"message":"hello',
    })
    _assert_equal(error, None, "missing closing quote plus brace error")
    _assert_equal(extraction_mode, "result_closure_repaired", "missing closing quote plus brace mode")
    _assert_equal(extracted, {"message": "hello"}, "missing closing quote plus brace extraction")


def _self_test_decoy_small_object_larger_real_object() -> None:
    real = {"real": True, "items": [1, 2, 3], "nested": {"value": "kept"}}
    result = 'prefix {"decoy":true} middle ' + json.dumps(real)
    extracted, extraction_mode, error = extract_envelope({
        "type": "result",
        "is_error": False,
        "result": result,
    })
    _assert_equal(error, None, "decoy object salvage error")
    _assert_equal(extraction_mode, "result_salvaged", "decoy object salvage mode")
    _assert_equal(extracted, real, "decoy object salvage extraction")


def _self_test_irreparable_garbage_fails() -> None:
    import contextlib
    import io

    extracted, _, error = extract_envelope({
        "type": "result",
        "is_error": False,
        "result": "not json at all",
    })
    _assert_equal(extracted, None, "irreparable garbage extraction")
    _assert(error is not None, "irreparable garbage error")

    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        exit_code = fail(error or "missing_error")
    _assert_equal(exit_code, 1, "irreparable garbage exit code")
    status = json.loads(stderr.getvalue())
    _assert_equal(status.get("status"), "fail", "irreparable garbage stderr status")


def _self_test_intact_json_unchanged() -> None:
    expected = {"role_id": "implementer", "items": [1, 2], "nested": {"ok": True}}
    extracted, extraction_mode, error = extract_envelope({
        "type": "result",
        "is_error": False,
        "result": json.dumps(expected),
    })
    _assert_equal(error, None, "intact JSON error")
    _assert_equal(extraction_mode, "result", "intact JSON mode")
    _assert_equal(extracted, expected, "intact JSON extraction")


def _self_test_raw_text_intact_json() -> None:
    import contextlib
    import io
    import tempfile

    expected = {"role_id": "implementer", "ok": True}
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / "raw.txt"
        out_path = Path(tmpdir) / "result.json"
        raw_path.write_text(json.dumps(expected), encoding="utf-8")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--raw-text", str(raw_path), "--out", str(out_path)])

        _assert_equal(exit_code, 0, "raw-text intact JSON exit code")
        status = json.loads(stdout.getvalue())
        _assert_equal(status.get("status"), "pass", "raw-text intact JSON status")
        _assert_equal(status.get("extraction_mode"), "result", "raw-text intact JSON mode")
        _assert_equal(json.loads(out_path.read_text(encoding="utf-8")), expected, "raw-text intact JSON extraction")


def _self_test_raw_text_truncated_json_repaired() -> None:
    import contextlib
    import io
    import tempfile

    expected = {"outer": {"inner": 1}}
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / "raw.txt"
        out_path = Path(tmpdir) / "result.json"
        raw_path.write_text('{"outer":{"inner":1}', encoding="utf-8")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--raw-text", str(raw_path), "--out", str(out_path)])

        _assert_equal(exit_code, 0, "raw-text truncated JSON exit code")
        status = json.loads(stdout.getvalue())
        _assert_equal(status.get("status"), "pass", "raw-text truncated JSON status")
        _assert_equal(status.get("extraction_mode"), "result_closure_repaired", "raw-text truncated JSON mode")
        _assert_equal(json.loads(out_path.read_text(encoding="utf-8")), expected, "raw-text truncated JSON extraction")


def _self_test_raw_text_embedded_json_salvaged() -> None:
    import contextlib
    import io
    import tempfile

    real = {"real": True, "items": [1, 2, 3], "nested": {"value": "kept"}}
    raw_text = 'prefix {"decoy":true} middle ' + json.dumps(real) + " suffix"
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / "raw.txt"
        out_path = Path(tmpdir) / "result.json"
        raw_path.write_text(raw_text, encoding="utf-8")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["--raw-text", str(raw_path), "--out", str(out_path)])

        _assert_equal(exit_code, 0, "raw-text embedded JSON exit code")
        status = json.loads(stdout.getvalue())
        _assert_equal(status.get("status"), "pass", "raw-text embedded JSON status")
        _assert_equal(status.get("extraction_mode"), "result_salvaged", "raw-text embedded JSON mode")
        _assert_equal(json.loads(out_path.read_text(encoding="utf-8")), real, "raw-text embedded JSON extraction")


def _self_test_raw_text_irreparable_garbage_fails() -> None:
    import contextlib
    import io
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = Path(tmpdir) / "raw.txt"
        out_path = Path(tmpdir) / "result.json"
        raw_path.write_text("not json at all", encoding="utf-8")

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = main(["--raw-text", str(raw_path), "--out", str(out_path)])

        _assert_equal(exit_code, 1, "raw-text irreparable garbage exit code")
        status = json.loads(stderr.getvalue())
        _assert_equal(status.get("status"), "fail", "raw-text irreparable garbage stderr status")
        _assert(not out_path.exists(), "raw-text irreparable garbage out file")


def run_self_tests() -> int:
    cases = [
        ("missing_single_closing_brace", _self_test_missing_single_closing_brace),
        ("missing_closing_quote_plus_brace", _self_test_missing_closing_quote_plus_brace),
        ("decoy_small_object_larger_real_object", _self_test_decoy_small_object_larger_real_object),
        ("irreparable_garbage_fails", _self_test_irreparable_garbage_fails),
        ("intact_json_unchanged", _self_test_intact_json_unchanged),
        ("raw_text_intact_json", _self_test_raw_text_intact_json),
        ("raw_text_truncated_json_repaired", _self_test_raw_text_truncated_json_repaired),
        ("raw_text_embedded_json_salvaged", _self_test_raw_text_embedded_json_salvaged),
        ("raw_text_irreparable_garbage_fails", _self_test_raw_text_irreparable_garbage_fails),
    ]
    results = []
    for name, test in cases:
        try:
            test()
        except AssertionError as exc:
            results.append({"name": name, "status": "fail", "error": str(exc)})
        else:
            results.append({"name": name, "status": "pass"})

    errors = [item for item in results if item["status"] != "pass"]
    print(json.dumps({"status": "pass" if not errors else "fail", "cases": results}, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract role JSON from Claude CLI JSON output.")
    parser.add_argument("--cli-output", help="Claude --output-format json file.")
    parser.add_argument("--raw-text", help="Raw text file containing a JSON object, truncated JSON object, or JSON object embedded in prose.")
    parser.add_argument("--out", help="Destination for extracted role JSON.")
    parser.add_argument("--self-test", action="store_true", help="Run extractor self-tests.")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_tests()

    if args.cli_output and args.raw_text:
        parser.error("--cli-output and --raw-text are mutually exclusive")

    if args.raw_text and not args.out:
        parser.error("--raw-text and --out are required unless --self-test is used")

    if not args.raw_text and (not args.cli_output or not args.out):
        parser.error("--cli-output and --out are required unless --self-test is used")

    out_path = Path(args.out)

    if args.raw_text:
        raw_text_path = Path(args.raw_text)
        try:
            raw_text = raw_text_path.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            return fail(f"raw_text_read_error: {exc}")

        extracted, extraction_mode, error = extract_raw_text(raw_text)
        if extracted is None:
            return fail(error or "extraction_failed")

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(extracted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"status": "pass", "out": str(out_path), "extraction_mode": extraction_mode}, ensure_ascii=False))
        return 0

    cli_output_path = Path(args.cli_output)

    try:
        envelope = json.loads(cli_output_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return fail(f"cli_output_parse_error: {exc}")

    extracted, extraction_mode, error = extract_envelope(envelope)
    if extracted is None:
        return fail(error or "extraction_failed")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(extracted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "out": str(out_path), "extraction_mode": extraction_mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
