from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet

from wxbot.storage import EncryptedJSONLStore, EncryptedJSONStore


def test_encrypted_json_store_roundtrip(tmp_path: Path):
    key = Fernet.generate_key()
    f = Fernet(key)
    p = tmp_path / "x.json.enc"
    s = EncryptedJSONStore(p, f)
    s.write({"a": 1, "b": "中文"})
    assert s.read() == {"a": 1, "b": "中文"}


def test_encrypted_jsonl_store_append_and_tail(tmp_path: Path):
    key = Fernet.generate_key()
    f = Fernet(key)
    p = tmp_path / "events.jsonl.enc"
    s = EncryptedJSONLStore(p, f)
    for i in range(10):
        s.append({"i": i})
    tail = s.tail(3)
    assert [x["i"] for x in tail] == [7, 8, 9]


def test_plain_jsonl_store_append_and_tail(tmp_path: Path):
    p = tmp_path / "events.jsonl"
    s = EncryptedJSONLStore(p, None)
    for i in range(5):
        s.append({"i": i})
    tail = s.tail(2)
    assert [x["i"] for x in tail] == [3, 4]


def test_plain_jsonl_append_and_trim(tmp_path: Path):
    p = tmp_path / "events.jsonl"
    s = EncryptedJSONLStore(p, None)
    for i in range(10):
        s.append_and_trim({"i": i}, max_lines=3)
    tail = s.tail(10)
    assert [x["i"] for x in tail] == [7, 8, 9]
