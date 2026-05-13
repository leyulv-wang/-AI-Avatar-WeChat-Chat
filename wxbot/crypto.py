from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet


def ensure_master_key(secrets_dir: Path, env_key: str | None) -> bytes:
    if env_key:
        return env_key.encode("utf-8")
    secrets_dir.mkdir(parents=True, exist_ok=True)
    key_path = secrets_dir / "master.key"
    if key_path.exists():
        return key_path.read_bytes().strip()
    key = Fernet.generate_key()
    tmp_path = secrets_dir / f".master.key.{os.getpid()}.tmp"
    tmp_path.write_bytes(key + b"\n")
    tmp_path.replace(key_path)
    return key


def get_fernet(master_key: bytes) -> Fernet:
    base64.urlsafe_b64decode(master_key)
    return Fernet(master_key)

