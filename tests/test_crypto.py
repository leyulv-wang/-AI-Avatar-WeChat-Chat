from __future__ import annotations

from pathlib import Path

from wxbot.crypto import ensure_master_key, get_fernet


def test_ensure_master_key_uses_env(tmp_path: Path):
    key = ensure_master_key(tmp_path, "Z0FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=")
    assert key == b"Z0FBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE="


def test_ensure_master_key_creates_and_persists(tmp_path: Path):
    secrets = tmp_path / "secrets"
    k1 = ensure_master_key(secrets, None)
    assert (secrets / "master.key").exists()
    k2 = ensure_master_key(secrets, None)
    assert k1 == k2
    f = get_fernet(k1)
    token = f.encrypt(b"x")
    assert f.decrypt(token) == b"x"

