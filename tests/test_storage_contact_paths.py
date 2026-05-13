from __future__ import annotations

from pathlib import Path

from wxbot.storage import get_contact_paths


def test_contact_paths_support_unicode_and_plain_suffix(tmp_path: Path):
    paths = get_contact_paths(tmp_path, "季珉如2.19", encrypt=False)
    assert paths.contact_dir.name == "季珉如2.19"
    assert paths.events_path.name.endswith(".jsonl")


def test_contact_paths_sanitize_invalid_chars(tmp_path: Path):
    paths = get_contact_paths(tmp_path, "a:b*c?d", encrypt=True)
    assert ":" not in paths.contact_dir.name
    assert "*" not in paths.contact_dir.name
    assert "?" not in paths.contact_dir.name

