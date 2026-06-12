from __future__ import annotations

from pathlib import Path

import pytest

import openplazma._json as json_module


def test_save_json_rejects_nonserializable_value_without_replacing_existing_file(tmp_path: Path):
    output_path = tmp_path / "record.json"
    original = '{"ok": true}\n'
    output_path.write_text(original, encoding="utf-8")

    with pytest.raises(ValueError, match="serializable"):
        json_module.save_json({"bad": object()}, output_path)

    assert output_path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob(".record.json.*.tmp")) == []


def test_save_json_keeps_existing_file_when_atomic_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_path = tmp_path / "record.json"
    original = '{"ok": true}\n'
    output_path.write_text(original, encoding="utf-8")

    def fail_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(json_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        json_module.save_json({"ok": False}, output_path)

    assert output_path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob(".record.json.*.tmp")) == []
